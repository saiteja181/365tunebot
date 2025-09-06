#!/usr/bin/env python3
"""
Simple test without Unicode characters
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_processor import SchemaProcessor  
from vector_db import VectorDatabase
from sql_generator import SQLQueryGenerator
from sql_executor import SQLExecutor
from result_processor import ResultProcessor

def simple_test():
    print("=== Simple NLP Q&A Test ===")
    
    try:
        # Initialize components
        print("Step 1: Initializing components...")
        schema_processor = SchemaProcessor("")
        vector_db = VectorDatabase()
        sql_generator = SQLQueryGenerator()
        sql_executor = SQLExecutor()
        result_processor = ResultProcessor()
        
        # Load existing data
        print("Step 2: Loading processed data...")
        schema_processor.load_processed_data("processed_schemas.json")
        vector_db.load_index("faiss_index.idx", "faiss_metadata.pkl")
        
        # Test query
        user_query = "show all users with active status"
        print(f"Step 3: Processing query: '{user_query}'")
        
        # Vector search
        print("Step 3a: Vector search...")
        faiss_results = vector_db.get_search_results_with_scores(user_query, top_k=3)
        relevant_tables = vector_db.get_relevant_tables(user_query, top_k=3) 
        print(f"Found {len(relevant_tables)} relevant tables: {relevant_tables}")
        
        for result in faiss_results:
            print(f"  - Table: {result.get('table_name', 'unknown')}")
            print(f"    Score: {result.get('relevance_score', 0):.3f}")
            print(f"    Preview: {result.get('schema_preview', 'no preview')}")
        
        # Get schemas
        print("Step 3b: Getting table schemas...")
        relevant_schemas = []
        for table_name in relevant_tables:
            schema_text = schema_processor.get_table_schema_text(table_name)
            if schema_text:
                relevant_schemas.append(schema_text)
                print(f"  - Schema for {table_name}: {len(schema_text)} characters")
        
        # Generate SQL
        print("Step 3c: Generating SQL query...")
        if relevant_schemas:
            sql_query = sql_generator.generate_sql_query(user_query, relevant_schemas)
            print(f"Generated SQL: {sql_query}")
            
            # Execute SQL  
            print("Step 3d: Executing SQL query...")
            success, results, execution_info, attempts = sql_executor.execute_query_with_retry(sql_query)
            
            if success:
                print(f"Execution successful! Retrieved {len(results)} rows")
                print(f"Execution info: {execution_info}")
                
                # Show sample results
                if results:
                    print("Sample results (first 2 rows):")
                    for i, row in enumerate(results[:2], 1):
                        print(f"  Row {i}: {dict(row)}")
                
                # Process to natural language
                print("Step 3e: Generating natural language response...")
                final_answer = result_processor.process_results_to_text(
                    user_query, sql_query, results, str(execution_info)
                )
                print(f"Final Answer: {final_answer}")
                
            else:
                print(f"SQL execution failed: {results}")
        else:
            print("No relevant schemas found")
            
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test()