#!/usr/bin/env python3
"""
Secure SQL Generator with Automatic Tenant Filtering
CRITICAL: ALL generated SQL queries MUST include tenant filtering
"""

import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML
from typing import List, Dict, Tuple, Optional, Any
from config import ask_o4_mini
from tenant_security import (
    TenantSecurityException,
    TenantValidator,
    audit_logger
)

class SecureSQLQueryGenerator:
    """
    Secure SQL Query Generator with mandatory tenant filtering

    This class ensures that ALL SQL queries are automatically filtered by tenant_code
    to prevent cross-tenant data access.
    """

    def __init__(self):
        # Tables that require tenant filtering
        self.tenant_tables = {'UserRecords', 'Licenses', 'TenantSummaries', 'UserGroupInfos'}

        # Cache schema between queries
        self._schema_cache = {}

        # Session SQL history for context (stores last 3 queries)
        self._session_sql_history = {}
        self._session_query_history = {}  # Store last 3 user queries too

        # System prompt for SQL generation
        self.system_prompt = """You are an expert SQL query generator for Microsoft 365 database.
Generate ONLY the SQL query without explanation.

AVAILABLE TABLES:
- UserRecords: User information (UserID, Mail, DisplayName, Department, AccountEnabled, IsLicensed, GroupIdsCsv, etc.)
- Licenses: License information (Id, Name, ActualCost, PartnerCost, ConsumedUnits, TotalUnits, Status)
- UserGroupInfos: Microsoft 365 Groups and Teams (Id, DisplayName, Description, Mail, MailEnabled, SecurityEnabled, MemberCount, OwnerCount, TeamId, Visibility, GroupTypes, CreatedDateTime, isArchived, LastModifiedDate, AssignedLicenses)
- TenantSummaries: Tenant-level aggregate data (TenantCode, TotalUsers, TotalActiveUsers, TotalInActiveUsers, TotalLicensedUsers, TotalSpend, TotalCostForInactiveUsers, TotalLicenseCount, TotalPaidLicenseCount, TotalFreeLicenseCount, AddedCostForAssignedLicenses, RemovedCostForNewUnAssignedLicenses, CaptureDate, etc.)

RESULT LIMITING RULES:
- By DEFAULT, use TOP 10 for list queries (e.g., "show users", "list licenses")
- If user says "all" / "show all" / "list all" / "display all" / "give me all" / "get all": DO NOT use TOP/LIMIT - return ALL rows
- Examples:
  * "Show all users" → SELECT * FROM UserRecords (NO TOP)
  * "List all licenses" → SELECT * FROM Licenses (NO TOP)
  * "Show users" → SELECT TOP 10 * FROM UserRecords (use TOP 10)

COST OPTIMIZATION QUERY PATTERNS (NEVER search for "optimization" in DisplayName!):
- "How can I optimize cost" / "optimize spending" / "reduce cost" / "cost savings" / "expensive licenses"
  → SELECT Name, TotalUnits, ConsumedUnits, COALESCE(ActualCost, PartnerCost) AS UnitCost,
     (CAST(ConsumedUnits as FLOAT) / NULLIF(TotalUnits, 0) * 100) as UtilizationPercent
  FROM Licenses WHERE TotalUnits > 0 ORDER BY UnitCost DESC
  This shows ALL licenses with their utilization - AI will analyze which ones have low utilization
  IMPORTANT: Do NOT filter by DisplayName containing "optimization" - that's wrong!

- "Most expensive licenses" / "highest cost licenses" / "top spending"
  → SELECT Name, COALESCE(ActualCost, PartnerCost) AS UnitCost, TotalUnits, ConsumedUnits
  FROM Licenses WHERE COALESCE(ActualCost, PartnerCost) > 0 ORDER BY UnitCost DESC

- "Unused licenses" / "underutilized licenses" / "wasted licenses"
  → SELECT Name, TotalUnits, ConsumedUnits, (TotalUnits - ConsumedUnits) AS UnusedUnits,
     COALESCE(ActualCost, PartnerCost) AS UnitCost
  FROM Licenses WHERE (TotalUnits - ConsumedUnits) > 0 ORDER BY UnusedUnits DESC

- "License utilization" / "how are licenses being used"
  → SELECT Name, TotalUnits, ConsumedUnits,
     (CAST(ConsumedUnits as FLOAT) / NULLIF(TotalUnits, 0) * 100) as UtilizationPercent
  FROM Licenses WHERE TotalUnits > 0 ORDER BY UtilizationPercent ASC

CRITICAL RULES:
1) AccountEnabled: 1=active, 0=inactive (bit column) - "inactive users" means AccountEnabled = 0
2) For costs: ALWAYS use COALESCE(l.ActualCost, l.PartnerCost) - never ActualCost alone, never SUM(ActualCost) alone
2b) CRITICAL - Total Spend Queries:
   - "What is our total spend" / "total license cost" / "total spend on licenses" / "license budget"
     → Query Licenses table DIRECTLY: SELECT SUM(COALESCE(ActualCost, PartnerCost)) FROM Licenses
     → This gives the ACTUAL total cost of all license SKUs
   - "Total cost for users" / "spending on users" / "user costs" / "cost per user"
     → Join UserRecords with Licenses (costs attributed to users)
   - "Most expensive licenses" / "show me licenses by cost" / "highest cost licenses"
     → Query: SELECT Name, COALESCE(ActualCost, PartnerCost) AS UnitCost, ConsumedUnits FROM Licenses WHERE COALESCE(ActualCost, PartnerCost) > 0 ORDER BY UnitCost DESC
     → NEVER use SUM(ActualCost) without COALESCE - ActualCost is often NULL!
   - For total spend, DEFAULT to Licenses table unless user specifically asks about users
3) JOIN Licenses: ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
4) To find users in a specific group ID: WHERE GroupIdsCsv LIKE '%group-id-here%' (NO JOIN needed!)
5) To find users who belong to ANY groups: WHERE GroupIdsCsv IS NOT NULL AND GroupIdsCsv != ''
6) GroupIdsCsv is a comma-separated list of group IDs - use LIKE to search it, NOT JOINs
7) Country codes: IN=India, US=USA, GB=UK, SA=Saudi, AE=UAE, CA=Canada, AU=Australia
8) Answer EXACTLY what's asked - no extra conditions
9) DO NOT add WHERE TenantCode clause - it will be added automatically for security
10) For groups/teams queries: Use UserGroupInfos table ONLY when querying group properties (DisplayName, MemberCount, etc)
11) Groups with Teams: Check TeamId IS NOT NULL or ResourceProvisioningOptions contains 'Team'
12) Security groups: SecurityEnabled = 1, Mail groups: MailEnabled = 1
13) Group visibility: Visibility column values are 'Public', 'Private', 'HiddenMembership'
13b) Licenses for a group: To get distinct license names for a group, use:
    SELECT DISTINCT l.Name FROM UserGroupInfos g
    JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%'
    JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
    WHERE g.DisplayName = 'GroupName'
    To COUNT distinct licenses: COUNT(DISTINCT l.Name) or COUNT(DISTINCT l.Id)
    AVOID STRING_AGG - use separate rows instead
14) GROUP COST AGGREGATION - CRITICAL FOR ACCURACY:
    When calculating TOTAL COST across multiple groups, ALWAYS use COUNT(DISTINCT ur.UserID)
    to avoid counting the same user multiple times if they belong to multiple groups.

    WRONG (counts same user multiple times):
    SELECT g.DisplayName, COUNT(ur.UserID) AS UserCount, SUM(COALESCE(l.ActualCost, l.PartnerCost)) AS TotalCost
    FROM UserGroupInfos g
    JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%'
    JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
    GROUP BY g.DisplayName

    CORRECT (counts each user once):
    SELECT g.DisplayName, COUNT(DISTINCT ur.UserID) AS UniqueUserCount, SUM(COALESCE(l.ActualCost, l.PartnerCost)) AS TotalCost
    FROM UserGroupInfos g
    JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%'
    JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
    GROUP BY g.DisplayName

    IMPORTANT: For accurate cost per group, use COUNT(DISTINCT ur.UserID) to count unique users only!
13c) CRITICAL - Listing groups with their licenses:
    DEFAULT BEHAVIOR: When asked about "groups with/and licenses" WITHOUT the words "how many", "count", or "number":
    - ALWAYS list actual license NAMES, not counts!
    - Query: SELECT DISTINCT g.DisplayName, l.Name FROM UserGroupInfos g JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%' JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%' ORDER BY g.DisplayName, l.Name
    - Returns one row per group-license pair (multiple rows per group if multiple licenses)
    - NEVER use STRING_AGG - it causes errors!
    - NEVER use COUNT unless question explicitly asks "how many" or "number of"
    - Examples needing LICENSE NAMES: "show groups with licenses", "list groups and licenses", "groups along with licenses", "display groups with their licenses", "get groups with associated licenses"
    ONLY use COUNT when: "how many licenses does each group have", "number of licenses per group", "count licenses for groups"
13d) CRITICAL - Group Name Matching with LIKE:
    - ALWAYS use LIKE operator with wildcards for group name matching to handle partial names
    - Users often mention partial group names (e.g., "365tune" when actual name is "365tune Group")
    - Use: WHERE g.DisplayName LIKE '%365tune%' (NOT = '365tune')
    - Examples:
      * User asks about "sales group" → WHERE g.DisplayName LIKE '%sales%'
      * User asks about "365tune" → WHERE g.DisplayName LIKE '%365tune%'
      * User asks about "marketing team" → WHERE g.DisplayName LIKE '%marketing%'
    - ONLY use exact match (=) when user provides the FULL group name in quotes or when context shows exact name
    - For multiple partial matches, return all matching groups to let user see options
15) For group costs: CRITICAL - Groups have users, users have licenses. Calculate group cost by:
    a) Find users in the group: WHERE ur.GroupIdsCsv LIKE '%group-id%'
    b) Join those users with Licenses: ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
    c) Sum the costs: SUM(COALESCE(l.ActualCost, l.PartnerCost))
    d) CRITICAL - ALWAYS use LEFT JOIN to show groups even if they have $0 cost!
    e) CRITICAL - ALWAYS use COUNT(DISTINCT ur.UserID) when counting users to avoid duplicates!

    Example for SINGLE group with UNIQUE user count:
        SELECT g.DisplayName, COUNT(DISTINCT ur.UserID) AS UniqueUsers, COALESCE(SUM(COALESCE(l.ActualCost, l.PartnerCost)), 0) AS TotalCost
        FROM UserGroupInfos g
        LEFT JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%'
        LEFT JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
        WHERE g.DisplayName LIKE '%GroupName%' OR g.Id = 'group-id'
        GROUP BY g.DisplayName

    Example for MULTIPLE groups with UNIQUE user counts:
        SELECT g.DisplayName, COUNT(DISTINCT ur.UserID) AS UniqueUsers, COALESCE(SUM(COALESCE(l.ActualCost, l.PartnerCost)), 0) AS TotalCost
        FROM UserGroupInfos g
        LEFT JOIN UserRecords ur ON ur.GroupIdsCsv LIKE '%'+g.Id+'%'
        LEFT JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
        GROUP BY g.DisplayName
        ORDER BY TotalCost DESC

    f) CRITICAL - For TOTAL/AGGREGATED group costs across ALL groups:
       Users can belong to MULTIPLE groups, so we need to ensure we don't count the same user's cost multiple times.
       BEST approach: First get distinct users in groups, then sum their license costs

       Example for TOTAL cost across ALL groups (counts each user's license cost ONCE):
            SELECT COUNT(DISTINCT ur.UserID) AS TotalUniqueUsers,
                   SUM(COALESCE(l.ActualCost, l.PartnerCost)) AS TotalGroupCost
            FROM (SELECT DISTINCT UserID FROM UserRecords WHERE GroupIdsCsv IS NOT NULL AND GroupIdsCsv != '') AS ur_distinct
            JOIN UserRecords ur ON ur_distinct.UserID = ur.UserID
            JOIN Licenses l ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'

       Keywords indicating need for aggregated DISTINCT user costs: "total", "all groups", "overall", "aggregate", "combined", "across all groups"
16) TenantSummaries: Use this table for AGGREGATE tenant-level queries (total spend, total users, etc.)
    - Contains historical data with CaptureDate for each snapshot
    - For current/latest data: SELECT TOP 1 ... FROM TenantSummaries ORDER BY CaptureDate DESC
    - For historical queries ("previous month", "last month", "January", specific dates):
      * Use CaptureDate to filter: WHERE MONTH(CaptureDate) = X AND YEAR(CaptureDate) = Y
      * Example for previous month: SELECT TOP 1 TotalSpend FROM TenantSummaries WHERE MONTH(CaptureDate) = MONTH(DATEADD(MONTH, -1, GETDATE())) AND YEAR(CaptureDate) = YEAR(DATEADD(MONTH, -1, GETDATE())) ORDER BY CaptureDate DESC
      * Example for specific month: SELECT TOP 1 TotalSpend FROM TenantSummaries WHERE MONTH(CaptureDate) = 10 AND YEAR(CaptureDate) = 2025 ORDER BY CaptureDate DESC
    - Contains pre-calculated totals - faster than computing from UserRecords/Licenses
17) Forecast/Expected costs: When user asks for "expected", "forecast", "projected", "annual" costs:
    - For ANNUAL forecast (remaining months in current year):
      * Get current month's spend and multiply by remaining months
      * Example: SELECT TOP 1 TotalSpend * (13 - MONTH(GETDATE())) AS RemainingYearForecast FROM TenantSummaries ORDER BY CaptureDate DESC
      * To include year-to-date + forecast: Add historical data from current year
    - For FULL YEAR forecast (12 months from now):
      * Multiply current spend by 12: SELECT TOP 1 (TotalSpend * 12) AS AnnualForecast FROM TenantSummaries ORDER BY CaptureDate DESC
    - For QUARTERLY forecast:
      * Multiply by 3: SELECT TOP 1 (TotalSpend * 3) AS QuarterlyForecast FROM TenantSummaries ORDER BY CaptureDate DESC
    - Keywords for remaining year: "rest of the year", "remaining", "until end of year"
    - Keywords for full year: "annual", "per year", "yearly", "next 12 months"
18) Date context: Today's date is available via GETDATE(). Use it for relative date calculations.
    - Current month: MONTH(GETDATE())
    - Previous month: DATEADD(MONTH, -1, GETDATE())
    - Months remaining in year: 13 - MONTH(GETDATE())"""

    def generate_sql_query_secure(self, user_query: str, relevant_schemas: List[str],
                                   tenant_code: str, conversation_context: str = "",
                                   session_id: str = "default") -> Tuple[str, Dict[str, Any]]:
        """
        Generate SQL query with MANDATORY tenant filtering using parameterized queries

        Args:
            user_query: User's natural language query
            relevant_schemas: List of relevant table schemas
            tenant_code: Tenant code to filter by (REQUIRED)
            conversation_context: Previous conversation context
            session_id: Session ID for context tracking

        Returns:
            Tuple of (SQL query with parameters, parameters dict)

        Raises:
            TenantSecurityException: If tenant_code is invalid or query cannot be secured
        """
        # CRITICAL: Validate tenant code
        is_valid, error_msg = TenantValidator.validate_tenant_code(tenant_code)
        if not is_valid:
            raise TenantSecurityException(f"Invalid tenant code: {error_msg}")

        # Generate base SQL query (without tenant filter)
        base_sql = self._generate_base_sql(user_query, relevant_schemas,
                                           conversation_context, session_id)

        if not base_sql:
            raise TenantSecurityException("Failed to generate SQL query")

        # INJECT tenant filter into the query with parameterization
        secured_sql, params = self._inject_tenant_filter(base_sql, tenant_code)

        # VALIDATE that tenant filter was successfully injected
        is_valid, error_msg = TenantValidator.validate_sql_has_tenant_filter(
            secured_sql, tenant_code
        )

        if not is_valid:
            # Log security violation
            audit_logger.log_security_violation(
                session_id, tenant_code,
                'tenant_filter_injection_failed',
                f"Failed to inject tenant filter: {error_msg}. Query: {base_sql[:200]}"
            )
            raise TenantSecurityException(f"Security validation failed: {error_msg}")

        # Store in session history (keep last 3 queries)
        if session_id not in self._session_sql_history:
            self._session_sql_history[session_id] = []
        if session_id not in self._session_query_history:
            self._session_query_history[session_id] = []

        self._session_sql_history[session_id].append(secured_sql)
        self._session_query_history[session_id].append(user_query)

        # Keep only last 3
        if len(self._session_sql_history[session_id]) > 3:
            self._session_sql_history[session_id] = self._session_sql_history[session_id][-3:]
        if len(self._session_query_history[session_id]) > 3:
            self._session_query_history[session_id] = self._session_query_history[session_id][-3:]

        return secured_sql, params

    def _generate_base_sql(self, user_query: str, relevant_schemas: List[str],
                           conversation_context: str, session_id: str) -> str:
        """
        Generate base SQL query (before tenant filter injection)

        Args:
            user_query: User's query
            relevant_schemas: Relevant table schemas
            conversation_context: Conversation context
            session_id: Session ID

        Returns:
            Base SQL query (without tenant filter)
        """
        # Cache key based on schemas
        schema_key = str(relevant_schemas)

        # Use cached schema summary if available
        if schema_key not in self._schema_cache:
            self._schema_cache[schema_key] = {
                'summary': self._create_minimal_schema(relevant_schemas),
                'columns': self._extract_available_columns("\n\n".join(relevant_schemas))
            }

        schema_summary = self._schema_cache[schema_key]['summary']
        available_columns = self._schema_cache[schema_key]['columns']

        # Get previous SQL queries from session history (last 3)
        previous_sqls = self._session_sql_history.get(session_id, [])
        previous_queries = self._session_query_history.get(session_id, [])

        # Build context prompt from previous queries
        sql_context = self._build_context_prompt(previous_sqls, previous_queries, user_query)

        # Build prompt
        if sql_context:
            prompt = f"""{self.system_prompt}
{sql_context}
Tables: {schema_summary}
Q: {user_query}
SQL:"""
        else:
            prompt = f"""{self.system_prompt}
Tables: {schema_summary}
Q: {user_query}
SQL:"""

        try:
            # Generate SQL using AI
            sql_query = ask_o4_mini(prompt, max_tokens=250)

            if sql_query:
                # Clean up response
                sql_query = sql_query.encode('ascii', errors='ignore').decode('ascii')
                sql_query = sql_query.strip()

            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            # Fix common errors
            sql_query = self._fix_common_column_errors(sql_query)
            sql_query = self._fix_select_star(sql_query)
            sql_query = sql_query.replace('FROM Users ', 'FROM UserRecords ')
            # Remove TenantCode placeholders from query (injected securely via parameterization)
            sql_query = re.sub(r"\s*AND\s+\w+\.TenantCode\s*=\s*'YourTenantCode'", "", sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(r"\s*WHERE\s+\w+\.TenantCode\s*=\s*'YourTenantCode'\s*AND", " WHERE", sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(r"\s*WHERE\s+\w+\.TenantCode\s*=\s*'YourTenantCode'", "", sql_query, flags=re.IGNORECASE)

            # Validate columns
            is_valid, invalid_cols = self._validate_query_columns(sql_query, available_columns)
            if not is_valid and invalid_cols:
                print(f"Warning: Query may contain invalid columns: {', '.join(set(invalid_cols))}")

            return sql_query

        except Exception as e:
            print(f"Error generating SQL query: {str(e)}")
            return ""

    def _inject_tenant_filter(self, sql_query: str, tenant_code: str) -> Tuple[str, Dict[str, Any]]:
        """
        Inject WHERE TenantCode = ? clause into SQL query with parameterization

        This is the CRITICAL security function that ensures tenant isolation.

        Args:
            sql_query: Original SQL query
            tenant_code: Tenant code to filter by

        Returns:
            Tuple of (SQL query with placeholders, parameters dict)

        Raises:
            TenantSecurityException: If injection fails
        """
        if not sql_query:
            raise TenantSecurityException("Cannot inject filter into empty query")

        # Sanitize tenant code
        tenant_code = TenantValidator.sanitize_tenant_code(tenant_code)

        # Parse the SQL query
        try:
            parsed = sqlparse.parse(sql_query)[0]
        except Exception as e:
            raise TenantSecurityException(f"Failed to parse SQL: {str(e)}")

        # Extract table aliases and names
        table_info = self._extract_tables_and_aliases(sql_query)

        # Determine which tables in the query need tenant filtering
        tables_needing_filter = []
        for table_name, alias in table_info:
            if table_name in self.tenant_tables:
                tables_needing_filter.append((table_name, alias))

        if not tables_needing_filter:
            # Query doesn't use tenant tables, no filter needed
            return sql_query, {}

        # Build tenant filter clause using parameterized queries
        tenant_filters = []
        params = {}
        for idx, (table_name, alias) in enumerate(tables_needing_filter):
            table_ref = alias if alias else table_name
            # Use parameterized query - safer than string concatenation
            param_name = f"tenant_code_{idx}"
            tenant_filters.append(f"{table_ref}.TenantCode = @{param_name}")
            params[param_name] = tenant_code

        combined_filter = " AND ".join(tenant_filters)

        # Inject the filter into the WHERE clause
        sql_upper = sql_query.upper()

        if 'WHERE' in sql_upper:
            # Query already has WHERE clause - add AND condition
            # Find WHERE position
            where_pos = sql_upper.find('WHERE')
            where_end = where_pos + 5  # len('WHERE')

            # Insert after WHERE
            secured_sql = (
                sql_query[:where_end] +
                f" {combined_filter} AND " +
                sql_query[where_end:]
            )
        else:
            # No WHERE clause - add one
            # Find position to insert (before GROUP BY, ORDER BY, or end)
            insert_keywords = ['GROUP BY', 'ORDER BY', 'HAVING', ';']
            insert_pos = len(sql_query)

            for keyword in insert_keywords:
                pos = sql_upper.find(keyword)
                if pos != -1 and pos < insert_pos:
                    insert_pos = pos

            # Insert WHERE clause
            secured_sql = (
                sql_query[:insert_pos].rstrip() +
                f" WHERE {combined_filter} " +
                sql_query[insert_pos:]
            )

        return secured_sql.strip(), params

    def _extract_tables_and_aliases(self, sql_query: str) -> List[Tuple[str, Optional[str]]]:
        """
        Extract table names and their aliases from SQL query

        Args:
            sql_query: SQL query

        Returns:
            List of tuples (table_name, alias_or_none)
        """
        tables = []

        # Simple regex-based extraction
        # Match: FROM TableName [alias] or JOIN TableName [alias]
        from_pattern = r'(?:FROM|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?'

        matches = re.finditer(from_pattern, sql_query, re.IGNORECASE)

        for match in matches:
            table_name = match.group(1)
            alias = match.group(2) if match.group(2) else None

            # Skip if alias is a SQL keyword
            sql_keywords = {'ON', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'INNER', 'LEFT', 'RIGHT', 'OUTER'}
            if alias and alias.upper() in sql_keywords:
                alias = None

            tables.append((table_name, alias))

        return tables

    def _create_minimal_schema(self, schemas: List[str]) -> str:
        """Create compact schema summary"""
        summary_parts = []
        for schema in schemas:
            lines = schema.split('\n')
            table_name = None
            columns = []

            for line in lines:
                line = line.strip()
                if line.startswith('Table:'):
                    table_name = line.split(':')[1].strip()
                elif line.startswith('- ') and table_name:
                    col_part = line.split(':')[0].strip('- ').strip()
                    if '(' in col_part:
                        col_name = col_part.split('(')[0].strip()
                    else:
                        col_name = col_part
                    columns.append(col_name)

            if table_name and columns:
                summary_parts.append(f"{table_name}({','.join(columns[:15])})")

        return "; ".join(summary_parts)

    def _extract_available_columns(self, schema_context: str) -> Dict[str, List[str]]:
        """Extract available columns from schema"""
        tables_columns = {}
        current_table = None

        for line in schema_context.split('\n'):
            line = line.strip()
            if line.startswith('Table:'):
                current_table = line.split(':')[1].strip()
                tables_columns[current_table] = []
            elif line.startswith('- ') and current_table:
                col_part = line.split(':')[0].strip('- ').strip()
                if '(' in col_part:
                    col_name = col_part.split('(')[0].strip()
                else:
                    col_name = col_part
                tables_columns[current_table].append(col_name)

        return tables_columns

    def _fix_common_column_errors(self, sql_query: str) -> str:
        """Fix common column name errors"""
        column_fixes = {
            'CreatedDate': 'CreateDate',
            'AccountStatus': 'AccountEnabled',
        }

        for wrong_col, correct_col in column_fixes.items():
            sql_query = sql_query.replace(wrong_col, correct_col)

        return sql_query

    def _fix_select_star(self, sql_query: str) -> str:
        """Replace SELECT * with explicit columns"""
        default_user_columns = "UserID, Mail, DisplayName, Department, ManagerName, UserType, AccountEnabled, IsLicensed, IsMFADisabled, LastSignInDateTime"

        if re.search(r'SELECT\s+\*\s+FROM\s+UserRecords', sql_query, re.IGNORECASE):
            sql_query = re.sub(
                r'SELECT\s+\*\s+FROM\s+UserRecords',
                f'SELECT {default_user_columns} FROM UserRecords',
                sql_query,
                flags=re.IGNORECASE
            )
            print(f"WARNING: Auto-fixed SELECT * to use explicit columns")

        return sql_query

    def _validate_query_columns(self, sql_query: str, available_columns: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
        """Validate query uses only available columns"""
        valid_columns = set()
        for table, cols in available_columns.items():
            valid_columns.update([col.lower() for col in cols])

        # Extract columns from query
        column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|>|<|LIKE|IN|IS|,|\))'
        potential_columns = re.findall(column_pattern, sql_query, re.IGNORECASE)

        sql_keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'like', 'as', 'on',
            'join', 'left', 'right', 'inner', 'outer', 'group', 'by', 'order', 'having',
            'count', 'sum', 'avg', 'max', 'min', 'top', 'distinct', 'null', 'true', 'false',
            'coalesce', 'isnull', 'cast', 'varchar', 'int', 'desc', 'asc', 'between',
            'float', 'nullif', 'case', 'when', 'then', 'else', 'end', 'year', 'month', 'day',
            # Common aliases that should not be flagged
            'unitcost', 'utilizationpercent', 'unusedunits', 'totalcost', 'avgcost',
            'usercount', 'activeusers', 'inactiveusers', 'licensedusers', 'totalgroupcost'
        }

        invalid_columns = []
        for col in potential_columns:
            col_lower = col.lower()
            if col_lower not in sql_keywords and not col.isdigit() and len(col) > 2:
                if col_lower not in valid_columns:
                    invalid_columns.append(col)

        return (len(invalid_columns) == 0, invalid_columns)

    def _build_context_prompt(self, previous_sqls: List[str], previous_queries: List[str], current_query: str) -> str:
        """Build context prompt from previous SQL queries (last 3)"""
        if not previous_sqls:
            return ""

        # Always provide context from previous queries - let AI decide if relevant
        context_parts = []

        # Process previous queries in reverse order (most recent first)
        for i in range(len(previous_sqls) - 1, -1, -1):
            prev_sql = previous_sqls[i]
            prev_query = previous_queries[i] if i < len(previous_queries) else ""

            sql_context = self._extract_sql_context(prev_sql)

            # Extract group name from previous query
            if sql_context['group_name']:
                context_parts.append(f"Previous query was about group: '{sql_context['group_name']}'")
                # If current query asks for breakdown/details, preserve the group filter
                if any(word in current_query.lower() for word in ['breakdown', 'break down', 'users', 'show me', 'list', 'details']):
                    context_parts.append(f"MAINTAIN GROUP FILTER: WHERE g.DisplayName LIKE '%{sql_context['group_name']}%'")
                break  # Use most recent group context

            # Extract department/country/entity filters
            if sql_context['entity_filter']:
                context_parts.append(f"Previous filter: {sql_context['entity_filter']}")

        # If we found context, return it
        if context_parts:
            return "CONTEXT from previous query: " + " | ".join(context_parts)

        return ""

    def _extract_sql_context(self, previous_sql: str) -> Dict[str, any]:
        """Extract context from previous SQL"""
        context = {
            'where_clauses': [],
            'join_clause': '',
            'calculation_type': '',
            'has_join': False,
            'group_name': '',
            'entity_filter': ''
        }

        if not previous_sql:
            return context

        # Extract group name from DisplayName LIKE or = conditions
        group_like_match = re.search(r"g\.DisplayName\s+LIKE\s+'%([^%]+)%'", previous_sql, re.IGNORECASE)
        if group_like_match:
            context['group_name'] = group_like_match.group(1)
        else:
            group_eq_match = re.search(r"g\.DisplayName\s*=\s*'([^']+)'", previous_sql, re.IGNORECASE)
            if group_eq_match:
                context['group_name'] = group_eq_match.group(1)

        # Extract department filter
        dept_match = re.search(r"Department\s*=\s*'([^']+)'", previous_sql, re.IGNORECASE)
        if dept_match:
            context['entity_filter'] = f"Department = '{dept_match.group(1)}'"

        # Extract country filter
        country_match = re.search(r"Country\s*=\s*'([^']+)'", previous_sql, re.IGNORECASE)
        if country_match:
            context['entity_filter'] = f"Country = '{country_match.group(1)}'"

        # Extract JOIN
        join_match = re.search(r'JOIN\s+\w+\s+\w+\s+ON\s+.*?(?=WHERE|GROUP|ORDER|$)',
                              previous_sql, re.IGNORECASE | re.DOTALL)
        if join_match:
            context['join_clause'] = join_match.group(0).strip()
            context['has_join'] = True

        # Extract WHERE clauses
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP\s+BY|ORDER\s+BY|$)',
                               previous_sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_content = where_match.group(1).strip()
            conditions = [c.strip() for c in re.split(r'\s+AND\s+', where_content, flags=re.IGNORECASE)]
            context['where_clauses'] = [c for c in conditions if c]

        # Detect calculation type
        sql_upper = previous_sql.upper()
        if 'COUNT(' in sql_upper:
            context['calculation_type'] = 'COUNT'
        elif 'SUM(' in sql_upper and 'COALESCE' in sql_upper:
            context['calculation_type'] = 'COST_SUM'
        elif 'SUM(' in sql_upper:
            context['calculation_type'] = 'SUM'

        return context

    def validate_and_improve_query(self, sql_query: str, error_message: str, schema_context: str) -> str:
        """
        Validate and improve SQL query based on error message

        Args:
            sql_query: The failed SQL query
            error_message: Error message from execution
            schema_context: Schema context for the query

        Returns:
            Improved SQL query or original if no improvement possible
        """
        if not sql_query or not error_message:
            return sql_query

        # Common fixes based on error patterns
        improved_query = sql_query

        # Fix invalid column name errors
        if 'Invalid column name' in error_message:
            # Extract the invalid column name
            match = re.search(r"Invalid column name '(\w+)'", error_message)
            if match:
                invalid_col = match.group(1)
                # Try common fixes
                column_mappings = {
                    'CreatedDate': 'CreateDate',
                    'CreateDateTime': 'CreatedDateTime',
                    'Status': 'AccountStatus',
                    'Email': 'Mail',
                    'Name': 'DisplayName',
                    'GroupName': 'DisplayName',
                    'Members': 'MemberCount',
                    'Owners': 'OwnerCount'
                }
                if invalid_col in column_mappings:
                    improved_query = improved_query.replace(invalid_col, column_mappings[invalid_col])

        # Fix table name errors
        if 'Invalid object name' in error_message:
            improved_query = improved_query.replace('FROM Users ', 'FROM UserRecords ')
            improved_query = improved_query.replace('FROM Groups ', 'FROM UserGroupInfos ')

        # Fix syntax errors with quotes
        if 'Unclosed quotation mark' in error_message:
            # Count quotes and try to fix
            single_quotes = improved_query.count("'")
            if single_quotes % 2 != 0:
                # Try to close unclosed quote at end
                improved_query = improved_query.rstrip() + "'"

        return improved_query
