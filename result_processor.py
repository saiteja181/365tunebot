from config import ask_o4_mini
from typing import List, Dict, Any
import json

class ResultProcessor:
    def __init__(self):
        self.system_prompt = """Convert SQL results to concise natural language. State facts only. No suggestions, tips, or questions. Be brief."""

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

        # Check if this is a cost-related query
        is_cost_query = any(word in query_lower for word in ['cost', 'spend', 'expensive', 'price', 'budget', 'financial'])
        cost_columns = ['TotalCost', 'EffectiveCost', 'TotalSpent', 'CostPerUser', 'AvgCost', 'ActualCost', 'PartnerCost']
        
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

        # CRITICAL FIX: For queries returning multiple rows, send more comprehensive data to AI
        # so it can accurately report all results, not just the first few
        max_preview_rows = 10 if total_rows <= 20 else 15

        for row in results[:max_preview_rows]:  # Increased to show more results
            filtered_row = {}
            for col in key_columns:
                if col in row and row[col] is not None:
                    filtered_row[col] = row[col]
            if filtered_row:  # Only add if we have meaningful data
                results_for_ai.append(filtered_row)

        # Create intelligent prompt that gives AI access to actual SQL results
        # Use actual count for count queries, otherwise use row count
        display_count = actual_count if actual_count is not None else total_rows

        # CRITICAL FIX: Send comprehensive results to AI, not just first 2 rows
        # For small result sets (<=15 rows), send ALL rows so AI sees everything
        # For larger sets, send first 10-15 rows + full statistics
        preview_limit = 15 if total_rows <= 15 else 10
        sql_results_preview = json.dumps(results[:preview_limit], default=str) if results else "[]"

        # CRITICAL FIX: Add result statistics for AI to understand full dataset
        result_stats = self._generate_result_statistics(results, query_lower)

        # Extract column names and their context from SQL query
        column_context = self._extract_column_context_from_sql(sql_query, user_query)

        prompt = f"""Question: {user_query}
SQL Query: {sql_query}
Results: {sql_results_preview}
Total rows returned: {len(results)}

{result_stats}

{column_context}

CRITICAL INSTRUCTIONS:
1. Use the EXACT column names from the Results when answering
2. If you see {len(results)} rows in Results, mention ALL {len(results)} items in your answer
3. The SQL query shows you what each column means (e.g., "COUNT(*) AS UserCount" means UserCount column has the count)
4. For list queries with multiple rows, enumerate or list ALL items you see in Results
5. Do NOT say "2 items" when there are actually {len(results)} items in Results
6. Be accurate about counts - if Results has 5 rows, say "5 items", not "2 items"

Describe the results briefly, accurately mentioning ALL items from Results. No suggestions."""
        
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
                # Try one more time with an even simpler prompt that includes full context
                simple_prompt = f"""User asked: {user_query}
SQL executed: {sql_query}
Results: {json.dumps(results[:preview_limit], default=str)}
Total rows: {len(results)}

{result_stats}

{column_context}

IMPORTANT: There are {len(results)} total rows. List or mention ALL {len(results)} items.
Answer the user's question using the exact column names from Results. Be concise."""
                response = ask_o4_mini(simple_prompt)
                
                if not response or len(response.strip()) < 10:
                    print("DEBUG: AI still failing, using fallback as last resort")
                    return self._create_enhanced_fallback_response(user_query, results, data_insights)
            
            # Validate response accuracy before returning
            validation_result = self._validate_response_accuracy(response, results, user_query)
            if not validation_result['is_valid']:
                print(f"WARNING: AI response may be inaccurate: {validation_result['warning']}")
                print(f"DEBUG: Attempting to fix response...")
                # Try to fix the response
                response = self._fix_inaccurate_response(response, results, user_query, validation_result)

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
            return f"No results found for your query: '{user_query}'."

        total_rows = len(results)

        # Create a conversational summary
        response = f"Found {total_rows:,} result{'s' if total_rows != 1 else ''}.\n\n"

        # Show key information from first few results in a readable format
        if total_rows > 0:
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
            response += f"... and {total_rows - 3:,} more record{'s' if total_rows - 3 != 1 else ''}."

        return response
    
    def _extract_column_context_from_sql(self, sql_query: str, user_query: str) -> str:
        """
        Extract column names from SQL query and map them to user's question context.
        This helps AI understand what SQL-generated column names mean.
        """
        import re

        if not sql_query:
            return ""

        context_parts = []

        # Parse SELECT clause to find computed columns
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)

            # Find AS aliases (computed columns)
            # Pattern: some_expression AS ColumnName
            alias_pattern = r'(\w+\([^)]*\)|\w+)\s+AS\s+(\w+)'
            aliases = re.findall(alias_pattern, select_clause, re.IGNORECASE)

            if aliases:
                context_parts.append("Column Meanings:")
                for expr, alias in aliases:
                    # Explain what the column means based on the expression
                    expr_upper = expr.upper()
                    if 'COUNT' in expr_upper:
                        context_parts.append(f"  - '{alias}' = count/number of records")
                    elif 'SUM' in expr_upper:
                        context_parts.append(f"  - '{alias}' = sum/total value")
                    elif 'AVG' in expr_upper:
                        context_parts.append(f"  - '{alias}' = average value")
                    elif 'MAX' in expr_upper:
                        context_parts.append(f"  - '{alias}' = maximum value")
                    elif 'MIN' in expr_upper:
                        context_parts.append(f"  - '{alias}' = minimum value")
                    else:
                        context_parts.append(f"  - '{alias}' = {expr}")

        # Add context from user query
        query_lower = user_query.lower()
        if 'how many' in query_lower or 'count' in query_lower:
            context_parts.append("\nUser wants a COUNT, so use the count column from Results.")
        elif 'total cost' in query_lower or 'spending' in query_lower:
            context_parts.append("\nUser wants TOTAL COST, so use the cost/sum column from Results.")

        return "\n".join(context_parts) if context_parts else ""

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

    def _generate_result_statistics(self, results: List[Dict], query_lower: str) -> str:
        """
        Generate comprehensive statistics about the full result set.
        This helps AI understand the complete dataset, not just the preview.
        """
        if not results:
            return "No results to analyze."

        stats = []
        total_rows = len(results)

        stats.append(f"DATASET SIZE: {total_rows} total rows")

        # For list queries, enumerate all unique values in key columns
        if total_rows <= 20 and any(word in query_lower for word in ['show', 'list', 'display', 'which', 'what']):
            # Get all unique values for important columns
            if results and isinstance(results[0], dict):
                first_row = results[0]

                # If results have DisplayName or Name, list ALL of them
                if 'DisplayName' in first_row:
                    all_names = [r.get('DisplayName') for r in results if r.get('DisplayName')]
                    if all_names:
                        stats.append(f"ALL ITEMS (DisplayName): {', '.join(all_names)}")
                elif 'Name' in first_row:
                    all_names = [r.get('Name') for r in results if r.get('Name')]
                    if all_names:
                        stats.append(f"ALL ITEMS (Name): {', '.join(all_names)}")

                # If results have group names and licenses, show the full mapping
                if 'DisplayName' in first_row and 'Name' in first_row:
                    all_pairs = [(r.get('DisplayName'), r.get('Name')) for r in results
                                if r.get('DisplayName') and r.get('Name')]
                    if all_pairs:
                        stats.append(f"COMPLETE LIST: {total_rows} group-license pairs")
                        # Show first 10 pairs explicitly
                        for i, (group, license) in enumerate(all_pairs[:10], 1):
                            stats.append(f"  {i}. {group} → {license}")
                        if len(all_pairs) > 10:
                            stats.append(f"  ... and {len(all_pairs) - 10} more pairs")

        # For aggregate queries (COUNT, SUM, etc.), extract the actual values
        if results and len(results) > 0:
            first_row = results[0]
            for col_name, value in first_row.items():
                col_lower = col_name.lower()
                # Identify aggregate columns
                if any(keyword in col_lower for keyword in ['count', 'total', 'sum', 'avg', 'max', 'min', 'cost', 'spend']):
                    if isinstance(value, (int, float)):
                        stats.append(f"AGGREGATE VALUE - {col_name}: {value}")

        return "\n".join(stats)

    def _validate_response_accuracy(self, response: str, results: List[Dict], user_query: str) -> Dict[str, Any]:
        """
        Validate that AI response accurately reflects the actual results.
        Checks for common issues like undercounting items.
        """
        if not response or not results:
            return {'is_valid': True}

        query_lower = user_query.lower()
        total_rows = len(results)

        # For list queries, check if AI mentions the correct number of items
        if total_rows <= 20 and any(word in query_lower for word in ['show', 'list', 'display', 'which', 'what', 'licenses']):
            # Extract all names/items from results
            if results and isinstance(results[0], dict):
                first_row = results[0]

                # For group-license queries
                if 'DisplayName' in first_row and 'Name' in first_row:
                    # This is a group-license mapping query
                    all_groups = set(r.get('DisplayName') for r in results if r.get('DisplayName'))
                    all_licenses = set(r.get('Name') for r in results if r.get('Name'))

                    # Check if response mentions the groups
                    mentioned_groups = sum(1 for group in all_groups if group.lower() in response.lower())

                    if mentioned_groups < len(all_groups) * 0.5:  # Less than 50% mentioned
                        return {
                            'is_valid': False,
                            'warning': f'Response mentions only {mentioned_groups}/{len(all_groups)} groups',
                            'expected_count': len(all_groups),
                            'actual_mentioned': mentioned_groups,
                            'type': 'group_license_undercount',
                            'all_groups': list(all_groups),
                            'all_licenses': list(all_licenses)
                        }

                # For simple list queries
                elif 'DisplayName' in first_row or 'Name' in first_row:
                    col_name = 'DisplayName' if 'DisplayName' in first_row else 'Name'
                    all_items = [r.get(col_name) for r in results if r.get(col_name)]

                    if all_items:
                        mentioned_count = sum(1 for item in all_items if item and item.lower() in response.lower())

                        if mentioned_count < len(all_items) * 0.5:  # Less than 50% mentioned
                            return {
                                'is_valid': False,
                                'warning': f'Response mentions only {mentioned_count}/{len(all_items)} items',
                                'expected_count': len(all_items),
                                'actual_mentioned': mentioned_count,
                                'type': 'list_undercount',
                                'all_items': all_items
                            }

        return {'is_valid': True}

    def _fix_inaccurate_response(self, response: str, results: List[Dict], user_query: str,
                                  validation_result: Dict[str, Any]) -> str:
        """
        Attempt to fix an inaccurate AI response.
        """
        if validation_result.get('type') == 'group_license_undercount':
            # For group-license queries, regenerate response with explicit list
            all_groups = validation_result.get('all_groups', [])
            total_pairs = len(results)

            fixed_response = f"Found {total_pairs} group-license associations across {len(all_groups)} groups:\n\n"
            fixed_response += "Groups with licenses:\n"

            # Group results by DisplayName
            from collections import defaultdict
            groups_dict = defaultdict(list)
            for row in results:
                group_name = row.get('DisplayName')
                license_name = row.get('Name')
                if group_name and license_name:
                    groups_dict[group_name].append(license_name)

            # List each group with its licenses
            for group, licenses in sorted(groups_dict.items()):
                fixed_response += f"- {group}: {', '.join(licenses)}\n"

            return fixed_response

        elif validation_result.get('type') == 'list_undercount':
            # For simple list queries, enumerate all items
            all_items = validation_result.get('all_items', [])
            fixed_response = f"Found {len(all_items)} items:\n"

            for i, item in enumerate(all_items, 1):
                fixed_response += f"{i}. {item}\n"

            return fixed_response.strip()

        # If we can't fix it, return original response
        return response

    def _enhance_response_formatting(self, response: str, total_rows: int, query_lower: str) -> str:
        """Enhance response formatting for better readability"""
        # Just return the response as-is, no additional formatting needed
        return response
    
    def _create_enhanced_fallback_response(self, user_query: str, results: List[Dict], data_insights: str) -> str:
        """Create an enhanced conversational response when AI processing fails"""
        if not results:
            return f"No results found for your query: '{user_query}'."

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
                    response = f"Found {actual_count} user in India."
                    # Get specific details about that user
                    user = results[0]
                    if 'DisplayName' in user and user['DisplayName']:
                        response += f" The user is {user['DisplayName']}"
                        if 'Department' in user and user['Department']:
                            response += f" from the {user['Department']} department"
                        response += "."
                else:
                    response = f"Found {actual_count:,} users in India."
            else:
                response = f"Found {total_rows:,} users in India."
        elif any(word in query_lower for word in ['how many', 'count']):
            entity = "records"
            if 'user' in query_lower:
                entity = "users"
            elif 'license' in query_lower:
                entity = "licenses"
            response = f"Found {display_count:,} {entity}."
        elif any(word in query_lower for word in ['list', 'show', 'display']):
            response = f"Found {total_rows:,} results:"
        else:
            response = f"Found {display_count:,} results."

        # Show meaningful examples
        if total_rows > 0 and total_rows <= 3:
            response += "\n\n"

            for i, row in enumerate(results[:3], 1):
                response += f"\nRecord {i}:\n"

                # Show most relevant fields in a user-friendly way
                if 'DisplayName' in row and row['DisplayName']:
                    response += f"   - Name: {row['DisplayName']}\n"
                if 'Department' in row and row['Department']:
                    response += f"   - Department: {row['Department']}\n"
                if 'Country' in row and row['Country']:
                    response += f"   - Location: {row['Country']}\n"
                if 'Mail' in row and row['Mail']:
                    response += f"   - Email: {row['Mail']}\n"
                if 'AccountStatus' in row and row['AccountStatus']:
                    response += f"   - Status: {row['AccountStatus']}\n"
        elif total_rows > 3:
            response += f" (Showing first 3 of {total_rows:,})\n\n"

            for i, row in enumerate(results[:3], 1):
                response += f"\nRecord {i}:\n"

                # Show most relevant fields in a user-friendly way
                if 'DisplayName' in row and row['DisplayName']:
                    response += f"   - Name: {row['DisplayName']}\n"
                if 'Department' in row and row['Department']:
                    response += f"   - Department: {row['Department']}\n"
                if 'Country' in row and row['Country']:
                    response += f"   - Location: {row['Country']}\n"
                if 'Mail' in row and row['Mail']:
                    response += f"   - Email: {row['Mail']}\n"
                if 'AccountStatus' in row and row['AccountStatus']:
                    response += f"   - Status: {row['AccountStatus']}\n"

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