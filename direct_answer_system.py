"""
Direct Answer System - Handles queries that don't need SQL execution
Returns answers from cached metadata, schema info, etc.
"""

from typing import Optional, Dict, List
import re

class DirectAnswerSystem:
    """Handles queries that can be answered without executing SQL"""

    def __init__(self, schema_processor=None):
        self.schema_processor = schema_processor
        self.stats = {
            'direct_answers': 0,
            'sql_bypassed': 0
        }

    def can_answer_directly(self, query: str) -> bool:
        """Check if this query can be answered without SQL"""
        query_lower = query.lower().strip()

        # Patterns that can be answered from metadata
        direct_patterns = [
            r'what (tables|table names) (are available|exist|do (you|we) have)',
            r'(list|show|what are) (the )?(available )?tables',
            r'what columns does (\w+) (table )?have',
            r'(list|show) columns (in|for|of) (\w+)',
            r'what (data|information) is available',
            r'what can (you|i) query',
            r'(explain|describe) (the )?(\w+) table',
            r'what (license types|licenses) (are available|exist)',
            r'(help|what can you do)',
            r'how (do i|to) (use this|query)',
        ]

        for pattern in direct_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def get_direct_answer(self, query: str) -> Optional[Dict]:
        """Get direct answer without SQL execution"""
        query_lower = query.lower().strip()

        # Pattern 1: What tables are available?
        if re.search(r'what (tables|table names)', query_lower):
            return self._answer_available_tables()

        # Pattern 2: What columns does [table] have?
        match = re.search(r'what columns does (\w+)', query_lower)
        if match:
            table_name = match.group(1)
            return self._answer_table_columns(table_name)

        # Pattern 3: List columns in [table]
        match = re.search(r'(list|show) columns (in|for|of) (\w+)', query_lower)
        if match:
            table_name = match.group(3)
            return self._answer_table_columns(table_name)

        # Pattern 4: What data is available?
        if re.search(r'what (data|information) is available', query_lower):
            return self._answer_available_data()

        # Pattern 5: What can I query?
        if re.search(r'what can (you|i) query', query_lower):
            return self._answer_query_capabilities()

        # Pattern 6: Help
        if re.search(r'^(help|what can you do)', query_lower):
            return self._answer_help()

        # Pattern 7: Explain/describe table
        match = re.search(r'(explain|describe) (the )?(\w+) table', query_lower)
        if match:
            table_name = match.group(3)
            return self._answer_table_description(table_name)

        return None

    def _answer_available_tables(self) -> Dict:
        """Answer: What tables are available?"""
        self.stats['direct_answers'] += 1
        self.stats['sql_bypassed'] += 1

        tables = ['UserRecords', 'Licenses']

        answer = "I have access to 2 main tables:\n\n"
        answer += "1. **UserRecords** - Contains information about users including:\n"
        answer += "   - User details (email, name, department)\n"
        answer += "   - Account status and login history\n"
        answer += "   - License assignments\n"
        answer += "   - Email and meeting activity\n\n"
        answer += "2. **Licenses** - Contains license information including:\n"
        answer += "   - License names and types\n"
        answer += "   - Costs (ActualCost and PartnerCost)\n"
        answer += "   - License status and expiration\n"
        answer += "   - Usage statistics"

        return {
            'answer_type': 'direct',
            'final_answer': answer,
            'sql_query': None,
            'results': {'tables': tables},
            'method': 'metadata'
        }

    def _answer_table_columns(self, table_name: str) -> Dict:
        """Answer: What columns does [table] have?"""
        self.stats['direct_answers'] += 1
        self.stats['sql_bypassed'] += 1

        # Normalize table name
        table_name_clean = table_name.capitalize()
        if table_name_clean == 'User' or table_name_clean == 'Users':
            table_name_clean = 'UserRecords'
        elif table_name_clean == 'License':
            table_name_clean = 'Licenses'

        if self.schema_processor:
            schema_text = self.schema_processor.get_table_schema_text(table_name_clean)

            # Extract just column names for a clean list
            columns = []
            for line in schema_text.split('\n'):
                if line.strip().startswith('- '):
                    col_name = line.split(':')[0].strip('- ').strip()
                    if '(' in col_name:
                        col_name = col_name.split('(')[0].strip()
                    columns.append(col_name)

            answer = f"The **{table_name_clean}** table has {len(columns)} columns:\n\n"

            # Group columns by category for UserRecords
            if table_name_clean == 'UserRecords':
                answer += "**Basic Info:** UserID, Mail, DisplayName, Department, UserType\n"
                answer += "**Account Status:** AccountStatus, AccountEnabled, IsLicensed, IsMFADisabled\n"
                answer += "**Login Info:** LastSignInDateTime, LastExchangeOnlineLogin, LastEntraIdLogin\n"
                answer += "**Activity:** EmailSent, EmailReceived, Meeting_Created_Count, Read_Count\n"
                answer += "**Licenses:** Licenses, LicenseAssignedDate\n"
                answer += "**Location:** Country, CountryCode, LastLogin_City, LastLogin_Country\n"
                answer += "**Management:** ManagerName, ManagerId\n"
                answer += f"\n📋 Full list: {', '.join(columns[:20])}..."
            elif table_name_clean == 'Licenses':
                answer += "**Basic:** Id, Name, Status\n"
                answer += "**Cost:** ActualCost, PartnerCost\n"
                answer += "**Usage:** ConsumedUnits, TotalUnits\n"
                answer += "**Dates:** CreateDateTime, LicenceExpirationDate\n"
                answer += "**Flags:** IsTrial, IsPaid, IsAddOn\n"
                answer += f"\n📋 Full list: {', '.join(columns)}"
            else:
                answer += ", ".join(columns)

            return {
                'answer_type': 'direct',
                'final_answer': answer,
                'sql_query': None,
                'results': {'columns': columns, 'table': table_name_clean},
                'method': 'schema_metadata'
            }

        return {
            'answer_type': 'direct',
            'final_answer': f"Table '{table_name_clean}' not found in schema.",
            'sql_query': None,
            'results': None,
            'method': 'schema_metadata'
        }

    def _answer_available_data(self) -> Dict:
        """Answer: What data is available?"""
        self.stats['direct_answers'] += 1
        self.stats['sql_bypassed'] += 1

        answer = """I can help you query Microsoft 365 user and license data:

📊 **User Information:**
- User profiles (email, name, department, manager)
- Account status (active, inactive, disabled)
- Login history and activity metrics
- Email and meeting statistics
- Location information

💼 **License Information:**
- License types and names (E1, E3, Teams, etc.)
- License costs and spending
- License assignments per user
- Usage and availability
- Trial vs. paid licenses

💡 **What you can ask:**
- "Find users in IT department"
- "Cost of licenses by department"
- "Users with E3 licenses"
- "Inactive users"
- "Which department spent the most?"

Need more help? Ask "what can I query?" for detailed examples!"""

        return {
            'answer_type': 'direct',
            'final_answer': answer,
            'sql_query': None,
            'results': None,
            'method': 'help'
        }

    def _answer_query_capabilities(self) -> Dict:
        """Answer: What can I query?"""
        return self._answer_available_data()

    def _answer_help(self) -> Dict:
        """Answer: Help or what can you do?"""
        self.stats['direct_answers'] += 1
        self.stats['sql_bypassed'] += 1

        answer = """👋 **Welcome! I'm your Microsoft 365 Analytics Assistant**

I can answer questions about your M365 users and licenses using natural language.

🎯 **Example Questions:**

**User Queries:**
- "Find users in the IT department"
- "How many active users do we have?"
- "Show inactive users"
- "Users from India"

**License Queries:**
- "Users with E3 licenses"
- "List all available licenses"
- "Cost of licenses by department"
- "Users without licenses"

**Cost Analysis:**
- "Which department spent the most on licenses?"
- "Total spending on M365 licenses"
- "License cost breakdown"

**Metadata:**
- "What tables are available?"
- "What columns does UserRecords have?"

💡 **Tips:**
- Ask naturally, like you're talking to a colleague
- I'll show you the SQL query I generate
- For complex queries, I can provide insights and recommendations

Try asking something now! 😊"""

        return {
            'answer_type': 'direct',
            'final_answer': answer,
            'sql_query': None,
            'results': None,
            'method': 'help'
        }

    def _answer_table_description(self, table_name: str) -> Dict:
        """Answer: Explain/describe [table]"""
        return self._answer_table_columns(table_name)

    def get_stats(self) -> Dict:
        """Get direct answer statistics"""
        return self.stats
