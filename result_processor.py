from config import ask_o4_mini
from typing import List, Dict, Any
import json

class ResultProcessor:
    def __init__(self):
        self.system_prompt = """You are a helpful assistant that converts SQL query results into natural language responses. 

Given:
1. The original user question
2. The SQL query that was executed
3. The results from the database

Your task is to:
1. Analyze the results and provide a clear, natural language answer to the user's question
2. Include relevant data points and insights from the results
3. If the results are empty, explain that clearly
4. Be concise but informative
5. Use proper formatting for numbers, dates, and lists when appropriate

Do not include the SQL query or raw data in your response unless specifically requested. Focus on answering the user's question directly."""

    def process_results_to_text(self, user_query: str, sql_query: str, results: List[Dict], execution_info: str) -> str:
        """Convert SQL results to natural language response with enhanced analysis"""
        
        if not results:
            return f"I didn't find any data matching your query '{user_query}'. You might want to try rephrasing your question or checking different search terms."
        
        # Enhanced analysis of query type and results
        query_lower = user_query.lower()
        total_rows = len(results)
        
        # Determine query intent for better responses
        is_count_query = any(word in query_lower for word in ['how many', 'count', 'number of'])
        is_list_query = any(word in query_lower for word in ['list', 'show', 'display', 'find'])
        is_specific_query = any(word in query_lower for word in ['who', 'which', 'what'])
        
        # Extract actual count/aggregate values for count queries
        actual_count = None
        if is_count_query and results:
            first_result = results[0]
            # Look for common count column names
            for col_name, value in first_result.items():
                if any(count_word in col_name.lower() for count_word in ['count', 'total', 'number']):
                    if isinstance(value, (int, float)):
                        actual_count = int(value)
                        break
        
        # Enhanced key columns based on query context
        key_columns = ['DisplayName', 'Mail', 'Department', 'Country', 'AccountStatus', 'UserType', 'IsLicensed', 'LastSignInDateTime']
        
        # Add contextual columns based on query
        if 'license' in query_lower:
            key_columns.extend(['IsLicensed', 'LicenseType'])
        if 'department' in query_lower:
            key_columns.insert(0, 'Department')
        if 'country' in query_lower:
            key_columns.insert(0, 'Country')
        
        # Extract and analyze data for better insights
        results_for_ai = []
        data_insights = self._analyze_results_patterns(results, query_lower)
        
        for row in results[:5]:  # Increased to 5 for better context
            filtered_row = {}
            for col in key_columns:
                if col in row and row[col] is not None:
                    filtered_row[col] = row[col]
            if filtered_row:  # Only add if we have meaningful data
                results_for_ai.append(filtered_row)
        
        # Create intelligent prompt that gives AI access to actual SQL results
        # Use actual count for count queries, otherwise use row count
        display_count = actual_count if actual_count is not None else total_rows
        
        # Give AI access to the actual SQL results for intelligent analysis
        sql_results_preview = json.dumps(results[:3], indent=1, default=str) if results else "[]"
        
        prompt = f"""User asked: "{user_query}"

SQL executed: {sql_query}
SQL returned {len(results)} rows with these results:
{sql_results_preview}

Based on the SQL results above, provide a natural, conversational answer to the user's question. 

If this is a count query, extract the actual count from the SQL results and mention it.
If this shows user data, mention relevant details like names, departments, countries.
Be helpful and suggest follow-up questions when appropriate.

Response:"""
        
        try:
            print("Step 4: Processing results with enhanced AI analysis...")
            print(f"DEBUG: Using display_count={display_count}, actual_count={actual_count}")
            print(f"DEBUG: Prompt length: {len(prompt)}")
            print(f"DEBUG: Prompt preview: {prompt[:200]}...")
            
            response = ask_o4_mini(prompt)
            
            print("Step 4: Enhanced AI processing completed successfully!")
            print(f"DEBUG: AI response length: {len(response) if response else 0}")
            print(f"DEBUG: AI response preview: {response[:100] if response else 'None'}...")
            
            # Check if response is valid
            if not response or len(response.strip()) < 10:
                print("DEBUG: AI response too short or empty, trying again with minimal prompt")
                # Try one more time with an even simpler prompt
                simple_prompt = f"The user asked '{user_query}' and got these SQL results: {json.dumps(results[:2], default=str)}. Give a natural answer."
                response = ask_o4_mini(simple_prompt)
                
                if not response or len(response.strip()) < 10:
                    print("DEBUG: AI still failing, using fallback as last resort")
                    return self._create_enhanced_fallback_response(user_query, results, data_insights)
            
            # Return the AI response directly (no additional formatting needed)
            return response.strip()
            
        except Exception as e:
            print(f"Step 4: AI processing failed with exception: {e}")
            print(f"DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            # Enhanced fallback response
            return self._create_enhanced_fallback_response(user_query, results, data_insights)
    
    def _create_fallback_response(self, user_query: str, results: List[Dict]) -> str:
        """Create a conversational response when AI processing fails"""
        if not results:
            return f"I couldn't find any results for your query: '{user_query}'. You might want to try rephrasing your question or checking if the data exists."
        
        total_rows = len(results)
        
        # Create a conversational summary
        response = f"I found {total_rows:,} result{'s' if total_rows != 1 else ''} for your query: '{user_query}'.\n\n"
        
        # Show key information from first few results in a readable format
        if total_rows > 0:
            response += "Here are some highlights from the results:\n\n"
            
            for i, row in enumerate(results[:3], 1):
                response += f"Record {i}:\n"
                
                # Show most relevant fields in a user-friendly way
                if 'DisplayName' in row and row['DisplayName']:
                    response += f"   - Name: {row['DisplayName']}\n"
                if 'Mail' in row and row['Mail']:
                    response += f"   - Email: {row['Mail']}\n"
                if 'Department' in row and row['Department']:
                    response += f"   - Department: {row['Department']}\n"
                if 'Country' in row and row['Country']:
                    response += f"   - Country: {row['Country']}\n"
                if 'AccountStatus' in row and row['AccountStatus']:
                    response += f"   - Status: {row['AccountStatus']}\n"
                
                response += "\n"
        
        if total_rows > 3:
            response += f"... and {total_rows - 3:,} more record{'s' if total_rows - 3 != 1 else ''}.\n\n"
        
        response += "TIP: For more detailed information, you can ask me specific questions about these results!"
        
        return response
    
    def _analyze_results_patterns(self, results: List[Dict], query_lower: str) -> str:
        """Analyze results to provide meaningful insights"""
        if not results:
            return "No data patterns to analyze."
        
        insights = []
        total_rows = len(results)
        
        # Analyze departments
        departments = [r.get('Department') for r in results if r.get('Department')]
        if departments:
            unique_depts = list(set(departments))
            if len(unique_depts) <= 5:
                insights.append(f"Departments: {', '.join(unique_depts)}")
            else:
                top_depts = list(set(departments))[:3]
                insights.append(f"Top departments include: {', '.join(top_depts)} (and {len(unique_depts)-3} others)")
        
        # Analyze countries
        countries = [r.get('Country') for r in results if r.get('Country')]
        if countries:
            unique_countries = list(set(countries))
            if len(unique_countries) <= 3:
                insights.append(f"Countries: {', '.join(unique_countries)}")
            else:
                insights.append(f"Spanning {len(unique_countries)} countries")
        
        # Analyze account status
        statuses = [r.get('AccountStatus') for r in results if r.get('AccountStatus')]
        if statuses:
            active_count = sum(1 for s in statuses if s == 'Active')
            if active_count > 0:
                active_pct = (active_count / len(statuses)) * 100
                insights.append(f"{active_pct:.0f}% are active users")
        
        # Analyze licensing
        licensing = [r.get('IsLicensed') for r in results if r.get('IsLicensed') is not None]
        if licensing:
            licensed_count = sum(1 for l in licensing if l)
            if licensed_count > 0:
                licensed_pct = (licensed_count / len(licensing)) * 100
                insights.append(f"{licensed_pct:.0f}% have licenses")
        
        return " - ".join(insights) if insights else "Standard user data analysis"
    
    def _enhance_response_formatting(self, response: str, total_rows: int, query_lower: str) -> str:
        """Enhance response formatting for better readability"""
        # Add indicators for better visual appeal
        if 'found' in response.lower() and total_rows > 0:
            if total_rows > 100:
                response = "RESULTS: " + response
            elif total_rows > 10:
                response = "DATA: " + response
            else:
                response = "INFO: " + response
        
        # Add helpful context based on query type
        if any(word in query_lower for word in ['list', 'show', 'display']) and total_rows > 5:
            response += f"\n\nTIP: This shows a sample of the {total_rows:,} results. Ask for more specific criteria to narrow down the list."
        
        return response
    
    def _create_enhanced_fallback_response(self, user_query: str, results: List[Dict], data_insights: str) -> str:
        """Create an enhanced conversational response when AI processing fails"""
        if not results:
            return f"I couldn't find any results for your query: '{user_query}'. You might want to try rephrasing your question or checking if the data exists."
        
        total_rows = len(results)
        query_lower = user_query.lower()
        
        # Extract actual count/aggregate values for count queries
        actual_count = None
        is_count_query = any(word in query_lower for word in ['how many', 'count', 'number of'])
        if is_count_query and results:
            first_result = results[0]
            # Look for common count column names
            for col_name, value in first_result.items():
                if any(count_word in col_name.lower() for count_word in ['count', 'total', 'number']):
                    if isinstance(value, (int, float)):
                        actual_count = int(value)
                        break
        
        # Use actual count for count queries, otherwise use row count
        display_count = actual_count if actual_count is not None else total_rows
        
        # Analyze query context for smarter responses
        if 'india' in query_lower and any(word in query_lower for word in ['how many', 'count', 'users']):
            if actual_count is not None:
                if actual_count == 1:
                    response = f"I found {actual_count} user in India in your Microsoft 365 tenant."
                    # Get specific details about that user
                    user = results[0]
                    if 'DisplayName' in user and user['DisplayName']:
                        response += f" The user is **{user['DisplayName']}**"
                        if 'Department' in user and user['Department']:
                            response += f" from the **{user['Department']}** department"
                        response += "."
                    response += "\n\nSince there's just one user in India, you might want to:"
                    response += "\n- Check their activity and license usage"
                    response += "\n- See their role and permissions"  
                    response += "\n- View their recent sign-in activity"
                else:
                    response = f"I found {actual_count:,} users in India in your Microsoft 365 tenant."
            else:
                response = f"I found {total_rows:,} users in India in your Microsoft 365 tenant."
        elif any(word in query_lower for word in ['how many', 'count']):
            entity = "records"
            if 'user' in query_lower:
                entity = "users"
            elif 'license' in query_lower:
                entity = "licenses"
            response = f"I found {display_count:,} {entity} matching your query."
        elif any(word in query_lower for word in ['list', 'show', 'display']):
            response = f"Here are the {total_rows:,} results I found for '{user_query}':"
        else:
            response = f"Based on your query '{user_query}', I found {display_count:,} relevant results."
        
        # Add insights
        if data_insights and data_insights != "Standard user data analysis":
            response += f"\n\n**Key insights:** {data_insights}"
        
        # Show meaningful examples
        if total_rows > 0:
            response += "\n\n**Sample results:**"
            
            for i, row in enumerate(results[:3], 1):
                response += f"\n\n**Record {i}:**"
                
                # Show most relevant fields in a user-friendly way
                if 'DisplayName' in row and row['DisplayName']:
                    response += f"\n   - **Name:** {row['DisplayName']}"
                if 'Department' in row and row['Department']:
                    response += f"\n   - **Department:** {row['Department']}"
                if 'Country' in row and row['Country']:
                    response += f"\n   - **Location:** {row['Country']}"
                if 'Mail' in row and row['Mail']:
                    response += f"\n   - **Email:** {row['Mail']}"
                if 'AccountStatus' in row and row['AccountStatus']:
                    response += f"\n   - **Status:** {row['AccountStatus']}"
        
        if total_rows > 3:
            response += f"\n\n... and **{total_rows - 3:,}** more results."
        
        # Add contextual helpful suggestions
        if 'india' in query_lower and total_rows == 1:
            response += "\n\n**You can ask me:**"
            response += "\n- 'What department is the India user in?'"
            response += "\n- 'When did the India user last sign in?'"
            response += "\n- 'What licenses does the India user have?'"
        elif 'user' in query_lower:
            response += "\n\n**Try asking:**"
            response += "\n- 'Show me users by department'"
            response += "\n- 'Which users are admins?'"
            response += "\n- 'How many active users do we have?'"
        else:
            response += "\n\n**Tip:** Ask me more specific questions to get detailed insights!"
        
        return response
    
    def create_summary_response(self, user_query: str, faiss_results: List[Dict], 
                               sql_query: str, sql_results: List[Dict], 
                               final_answer: str, execution_info: str) -> Dict:
        """Create a comprehensive response with all intermediate results"""
        
        return {
            'user_query': user_query,
            'step_1_vector_search': {
                'description': 'FAISS Vector Search Results - Most relevant tables found:',
                'results': faiss_results
            },
            'step_2_sql_generation': {
                'description': 'Generated SQL Query:',
                'sql_query': sql_query
            },
            'step_3_sql_execution': {
                'description': 'SQL Query Execution Results:',
                'execution_info': execution_info,
                'result_count': len(sql_results) if sql_results else 0,
                'sample_results': sql_results[:5] if sql_results else []  # First 5 rows
            },
            'step_4_final_answer': {
                'description': 'Natural Language Answer:',
                'answer': final_answer
            }
        }
    
    def format_response_for_display(self, summary: Dict) -> str:
        """Format the comprehensive response for nice console display"""
        output = []
        
        output.append("=" * 80)
        output.append(f"QUERY: {summary['user_query']}")
        output.append("=" * 80)
        
        # Step 1: Vector Search
        output.append("\nSTEP 1: VECTOR SEARCH RESULTS")
        output.append("-" * 40)
        faiss_results = summary['step_1_vector_search']['results']
        for i, result in enumerate(faiss_results, 1):
            output.append(f"{i}. Table: {result['table_name']} (Score: {result['relevance_score']})")
            output.append(f"   Preview: {result['schema_preview']}")
        
        # Step 2: SQL Generation  
        output.append("\nSTEP 2: GENERATED SQL QUERY")
        output.append("-" * 40)
        output.append(summary['step_2_sql_generation']['sql_query'])
        
        # Step 3: SQL Execution
        output.append("\nSTEP 3: SQL EXECUTION RESULTS")
        output.append("-" * 40)
        output.append(summary['step_3_sql_execution']['execution_info'])
        
        sample_results = summary['step_3_sql_execution']['sample_results']
        if sample_results:
            output.append("\nSample Results:")
            for i, row in enumerate(sample_results, 1):
                output.append(f"Row {i}: {dict(row)}")
        
        # Step 4: Final Answer
        output.append("\nSTEP 4: FINAL ANSWER")
        output.append("-" * 40)
        output.append(summary['step_4_final_answer']['answer'])
        
        output.append("\n" + "=" * 80)
        
        return "\n".join(output)