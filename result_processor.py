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
        """Convert SQL results to natural language response"""
        
        if not results:
            return f"No data was found that matches your query: '{user_query}'"
        
        # Prepare the results for the AI (limit size and select key columns only)
        key_columns = ['DisplayName', 'Mail', 'Department', 'Country', 'AccountStatus', 'UserType', 'IsLicensed', 'LastSignInDateTime']
        
        # Extract only key columns from first few rows
        results_for_ai = []
        for row in results[:3]:  # Only 3 rows for speed
            filtered_row = {}
            for col in key_columns:
                if col in row:
                    filtered_row[col] = row[col]
            results_for_ai.append(filtered_row)
        
        results_summary = {
            'total_rows': len(results),
            'sample_data': results_for_ai,
            'columns': key_columns
        }
        
        # Create shorter, more focused prompt to reduce processing time
        prompt = f"""You are a helpful assistant that provides natural language answers to database queries.

User asked: "{user_query}"
SQL Query executed: {sql_query}
Total results: {len(results)} records found

Sample data (key fields only):
{json.dumps(results_for_ai, indent=1, default=str)}

Please provide a friendly, conversational answer that:
1. Starts with a summary (e.g., "I found X users/records that match your query")
2. Highlights key insights or patterns from the data
3. Mentions a few specific examples if relevant
4. Uses natural language, not technical jargon
5. Keep it concise but informative

Answer:"""
        
        try:
            print("Step 4: Processing results with AI...")
            response = ask_o4_mini(prompt)
            print("Step 4: AI processing completed successfully!")
            return response.strip()
        except Exception as e:
            print(f"Step 4: AI processing failed: {e}")
            # Fallback response if AI processing fails
            return self._create_fallback_response(user_query, results)
    
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
                response += f"📋 Record {i}:\n"
                
                # Show most relevant fields in a user-friendly way
                if 'DisplayName' in row and row['DisplayName']:
                    response += f"   • Name: {row['DisplayName']}\n"
                if 'Mail' in row and row['Mail']:
                    response += f"   • Email: {row['Mail']}\n"
                if 'Department' in row and row['Department']:
                    response += f"   • Department: {row['Department']}\n"
                if 'Country' in row and row['Country']:
                    response += f"   • Country: {row['Country']}\n"
                if 'AccountStatus' in row and row['AccountStatus']:
                    response += f"   • Status: {row['AccountStatus']}\n"
                
                response += "\n"
        
        if total_rows > 3:
            response += f"... and {total_rows - 3:,} more record{'s' if total_rows - 3 != 1 else ''}.\n\n"
        
        response += "💡 For more detailed information, you can ask me specific questions about these results!"
        
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