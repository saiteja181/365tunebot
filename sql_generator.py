from config import ask_o4_mini
from typing import List, Dict

class SQLQueryGenerator:
    def __init__(self):
        self.system_prompt = """You are an expert SQL query generator. Given a natural language question, relevant database schema information, and optional conversation context, generate a precise SQL query.

Guidelines:
1. Generate only the SQL query without any explanation or formatting
2. Use proper SQL syntax for SQL Server
3. Be precise and avoid unnecessary complexity
4. Use appropriate JOIN clauses when needed
5. Include relevant WHERE clauses based on the question
6. Use appropriate aggregate functions when needed
7. Return only the SQL query, nothing else
8. CONTEXT HANDLING: If conversation context is provided, analyze it to understand:
   - Previous filters or conditions that should be maintained
   - References to specific data from previous queries
   - Follow-up questions that build upon previous results
   - Comparative queries (e.g., "compared to that", "same department", "those users")
   - Implicit assumptions based on prior conversation

License Name Mappings (use these exact names in LIKE or = comparisons):
- E1 = "Office 365 E1"
- E3 = "Microsoft 365 E3" 
- Teams = "Microsoft Teams" (various variations exist)
- Power BI = "Power BI Pro" or "Power BI Premium Per User"
- Intune = "Intune"
- Defender = "Microsoft Defender" (various types exist)
- Copilot = "Microsoft_365_Copilot" or "Microsoft Copilot Studio"

Available License Names in Database:
Microsoft 365 E3, Intune, Project Online Premium, Office 365 E1, Microsoft Teams Audio Conferencing with dial-out to USA/CAN, Microsoft Stream, Microsoft Teams Shared Devices, Dynamics 365 Field Service Viral Trial, M365_INFO_PROTECTION_GOVERNANCE, Microsoft Teams Premium Introductory Pricing, Microsoft Teams Phone Resource Account, Power Automate per user plan, Microsoft Copilot Studio User License, Microsoft Teams Rooms Pro, Microsoft Defender for Office 365 (Plan 1), Teams Premium (for Departments), Planner and Project Plan 3, Microsoft_365_Copilot, Windows Store for Business, Win10_VDA_E3, Microsoft Teams Rooms Basic, Microsoft Copilot Studio, Microsoft Entra ID P2, Rights Management Adhoc, App Connect IW, Microsoft Defender for Identity, Office 365 Extra File Storage, Microsoft Fabric (Free), Power Apps Premium, Dynamics 365 Customer Voice Trial, Power BI Premium Per User, VISIOCLIENT, Microsoft Power Apps Plan 2 Trial, Microsoft Teams Phone Standard, Power Automate Premium, Enterprise Mobility + Security E3, Microsoft Power Automate Free, Power BI Pro, Microsoft 365 Business Basic, Communications Credits, Microsoft 365 Business Premium, Microsoft Teams Exploratory Dept, Microsoft Defender for Business

Country Code Mappings (use ISO country codes):
- India = 'IN'
- United States = 'US'
- Canada = 'CA'
- United Kingdom = 'GB'
- Saudi Arabia = 'SA'
- UAE/Emirates = 'AE'
- Qatar = 'QA'
- Iraq = 'IQ'
- Australia = 'AU'
- Russia = 'RU'
- Mozambique = 'MZ'

Schema format will be provided as:
Table: table_name
Columns:
  - column_name (data_type): description

Important Notes:
- The UserRecords table contains user information and a "Licenses" column that contains license IDs (GUIDs) separated by commas
- The Licenses table contains detailed license information with Id, Name, ActualCost, PartnerCost, etc.
- To get cost information by department, you need to JOIN UserRecords with Licenses using: JOIN Licenses l ON ur.Licenses LIKE '%' + l.Id + '%'
- For M365 licenses, filter using: l.Name LIKE '%Microsoft 365%' OR l.Name LIKE '%Office 365%'
- Use SUM(l.ActualCost) or SUM(l.PartnerCost) for calculating total spending
- Group by ur.Department for department-level analysis
- The UserRecords.Licenses column contains comma-separated GUIDs like: '4ef96642-f096-40de-a3e9-d83fb2f90211,05e9a617-0261-4cee-bb44-138d3ef5d965'
- Always filter out records where ur.Licenses IS NOT NULL and ur.Department IS NOT NULL
- For country-based queries, use ISO country codes: LastLogin_Country = 'IN' (for India), 'US' (for USA), etc.
- When asked for "which department spent more/most", return the department with highest spending, use ORDER BY TotalSpent DESC and TOP 1
- When asked for "spending by department", show all departments with ORDER BY TotalSpent DESC

CRITICAL - Account Status Rules:
- The UserRecords table has AccountStatus column with values: 'Active', 'Disabled', 'Inactive'
- For ACTIVE users: use AccountStatus = 'Active'
- For INACTIVE users: use AccountStatus IN ('Disabled', 'Inactive') OR AccountStatus != 'Active'
- NEVER use AccountEnabled column for active/inactive queries
- For "inactive users" questions, always use AccountStatus != 'Active'
- For "disabled users" questions, use AccountStatus = 'Disabled'
- For "all users except active" questions, use AccountStatus != 'Active'
"""
    
    def generate_sql_query(self, user_query: str, relevant_schemas: List[str], conversation_context: str = "") -> str:
        """Generate SQL query based on user question, relevant schemas, and conversation context"""
        
        # Combine schemas into context
        schema_context = "\n\n".join(relevant_schemas)
        
        # Create context-aware prompt
        context_section = ""
        if conversation_context and conversation_context.strip():
            context_section = f"""
Conversation Context (for reference and continuity):
{conversation_context}

Important: Use the conversation context to understand:
- What tables or data the user was previously asking about
- Any filters, conditions, or specific criteria mentioned before
- References to previous results (e.g., "those users", "same department", "from that query")
- Follow-up questions that build on previous queries
- Comparative questions (e.g., "compared to the previous result")

"""
        
        # Create the prompt
        prompt = f"""{self.system_prompt}
{context_section}
Database Schema:
{schema_context}

Current User Question: {user_query}

Generate the SQL query that answers the current question, taking into account the conversation context if provided:"""
        
        try:
            sql_query = ask_o4_mini(prompt)
            # Clean up the response (remove any markdown formatting, etc.)
            sql_query = sql_query.strip()
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()
            
            return sql_query
        except Exception as e:
            print(f"Error generating SQL query: {str(e)}")
            return ""
    
    def validate_and_improve_query(self, sql_query: str, error_message: str = None) -> str:
        """Validate and improve SQL query if there was an execution error"""
        if not error_message:
            return sql_query
        
        improvement_prompt = f"""The following SQL query resulted in an error:

SQL Query: {sql_query}

Error: {error_message}

Please provide a corrected version of the SQL query that fixes this error. Return only the corrected SQL query without any explanation:"""
        
        try:
            improved_query = ask_o4_mini(improvement_prompt)
            improved_query = improved_query.strip()
            if improved_query.startswith("```sql"):
                improved_query = improved_query.replace("```sql", "").replace("```", "").strip()
            elif improved_query.startswith("```"):
                improved_query = improved_query.replace("```", "").strip()
            
            return improved_query
        except Exception as e:
            print(f"Error improving SQL query: {str(e)}")
            return sql_query
    
    def generate_contextual_query_with_fallback(self, user_query: str, relevant_schemas: List[str], conversation_context: str = "") -> str:
        """Generate SQL query with context, with automatic fallback if context causes issues"""
        
        # First try with context if provided
        if conversation_context:
            try:
                contextual_query = self.generate_sql_query(user_query, relevant_schemas, conversation_context)
                # Basic validation: check if query looks reasonable
                if contextual_query and len(contextual_query.strip()) > 10 and "SELECT" in contextual_query.upper():
                    return contextual_query
                else:
                    print("Contextual query appears invalid, falling back to non-contextual query")
            except Exception as e:
                print(f"Error generating contextual query: {e}, falling back to non-contextual query")
        
        # Fallback to non-contextual query
        return self.generate_sql_query(user_query, relevant_schemas, "")