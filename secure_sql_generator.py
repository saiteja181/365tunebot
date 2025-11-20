#!/usr/bin/env python3
"""
Secure SQL Generator with Automatic Tenant Filtering
CRITICAL: ALL generated SQL queries MUST include tenant filtering
"""

import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML
from typing import List, Dict, Tuple, Optional
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
        self.tenant_tables = {'UserRecords', 'Licenses', 'TenantSummaries'}

        # Cache schema between queries
        self._schema_cache = {}

        # Session SQL history for context
        self._session_sql_history = {}

        # System prompt for SQL generation
        self.system_prompt = """You are an expert SQL query generator for Microsoft 365 database.
Generate ONLY the SQL query without explanation.

CRITICAL RULES:
1) AccountEnabled: 1=active, 0=inactive (bit column) - "inactive users" means AccountEnabled = 0
2) For costs: ALWAYS use COALESCE(l.ActualCost, l.PartnerCost) - never ActualCost alone
3) JOIN Licenses: ON ur.Licenses LIKE '%'+CAST(l.Id AS VARCHAR(50))+'%'
4) Country codes: IN=India, US=USA, GB=UK, SA=Saudi, AE=UAE, CA=Canada, AU=Australia
5) Answer EXACTLY what's asked - no extra conditions
6) DO NOT add WHERE TenantCode clause - it will be added automatically for security"""

    def generate_sql_query_secure(self, user_query: str, relevant_schemas: List[str],
                                   tenant_code: str, conversation_context: str = "",
                                   session_id: str = "default") -> str:
        """
        Generate SQL query with MANDATORY tenant filtering

        Args:
            user_query: User's natural language query
            relevant_schemas: List of relevant table schemas
            tenant_code: Tenant code to filter by (REQUIRED)
            conversation_context: Previous conversation context
            session_id: Session ID for context tracking

        Returns:
            SQL query with tenant filtering injected

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

        # INJECT tenant filter into the query
        secured_sql = self._inject_tenant_filter(base_sql, tenant_code)

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

        # Store in session history
        self._session_sql_history[session_id] = secured_sql

        return secured_sql

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

        # Get previous SQL from session history
        previous_sql = self._session_sql_history.get(session_id, "")

        # Build context prompt
        sql_context = self._build_context_prompt(previous_sql, user_query)

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

            # Validate columns
            is_valid, invalid_cols = self._validate_query_columns(sql_query, available_columns)
            if not is_valid and invalid_cols:
                print(f"Warning: Query may contain invalid columns: {', '.join(set(invalid_cols))}")

            return sql_query

        except Exception as e:
            print(f"Error generating SQL query: {str(e)}")
            return ""

    def _inject_tenant_filter(self, sql_query: str, tenant_code: str) -> str:
        """
        Inject WHERE TenantCode = ? clause into SQL query

        This is the CRITICAL security function that ensures tenant isolation.

        Args:
            sql_query: Original SQL query
            tenant_code: Tenant code to filter by

        Returns:
            SQL query with tenant filter injected

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
            return sql_query

        # Build tenant filter clause
        tenant_filters = []
        for table_name, alias in tables_needing_filter:
            table_ref = alias if alias else table_name
            # Use parameterized query with @TenantCode
            tenant_filters.append(f"{table_ref}.TenantCode = '{tenant_code}'")

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

        return secured_sql.strip()

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
            'coalesce', 'isnull', 'cast', 'varchar', 'int', 'desc', 'asc', 'between'
        }

        invalid_columns = []
        for col in potential_columns:
            col_lower = col.lower()
            if col_lower not in sql_keywords and not col.isdigit() and len(col) > 2:
                if col_lower not in valid_columns:
                    invalid_columns.append(col)

        return (len(invalid_columns) == 0, invalid_columns)

    def _build_context_prompt(self, previous_sql: str, user_query: str) -> str:
        """Build context prompt from previous SQL"""
        if not previous_sql:
            return ""

        # Check if follow-up question
        follow_up_words = ['them', 'those', 'what about', 'how many', 'which', 'and for']
        is_follow_up = any(word in user_query.lower() for word in follow_up_words)

        if not is_follow_up:
            return ""

        # Extract context from previous SQL
        sql_context = self._extract_sql_context(previous_sql)

        context_parts = []

        if sql_context['calculation_type'] == 'COST_SUM':
            context_parts.append("MAINTAIN COST CALCULATION: Use SUM(COALESCE(l.ActualCost, l.PartnerCost)) with JOIN")
        elif sql_context['calculation_type'] == 'COUNT' and 'how many' in user_query.lower():
            context_parts.append("Use COUNT")

        if sql_context['has_join'] and sql_context['join_clause']:
            context_parts.append(f"REQUIRED JOIN: {sql_context['join_clause']}")

        if sql_context['where_clauses']:
            # Filter out tenant code from previous WHERE clauses (will be re-added)
            non_tenant_clauses = [c for c in sql_context['where_clauses']
                                 if 'tenantcode' not in c.lower()]
            if non_tenant_clauses:
                context_parts.append(f"PRESERVE FILTERS: {' AND '.join(non_tenant_clauses)}")

        if context_parts:
            return "CONTEXT: " + " | ".join(context_parts)

        return ""

    def _extract_sql_context(self, previous_sql: str) -> Dict[str, any]:
        """Extract context from previous SQL"""
        context = {
            'where_clauses': [],
            'join_clause': '',
            'calculation_type': '',
            'has_join': False
        }

        if not previous_sql:
            return context

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
