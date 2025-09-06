#!/usr/bin/env python3
"""
Quick Text-to-SQL System - Lightweight version for testing
"""

import os
import sys
from typing import Optional

from schema_processor import SchemaProcessor
from sql_generator import SQLQueryGenerator
from sql_executor import SQLExecutor
from result_processor import ResultProcessor

class QuickTextToSQLSystem:
    def __init__(self):
        self.schema_processor = SchemaProcessor("")
        self.sql_generator = SQLQueryGenerator()
        self.sql_executor = SQLExecutor()
        self.result_processor = ResultProcessor()
        self.is_initialized = False
        self.schema_text = ""
    
    def initialize_system(self, csv_file_path: str):
        """Initialize the system with schema data"""
        print("Initializing Quick Text-to-SQL System...")
        
        # Process schema from CSV
        print(f"Processing schema from CSV: {csv_file_path}")
        self.schema_processor = SchemaProcessor(csv_file_path)
        schema_data = self.schema_processor.process_csv_schema()
        
        if not schema_data:
            print("Failed to process schema data!")
            return False
        
        # Create a simple text representation of all schemas
        self.schema_text = self.schema_processor.get_table_schema_text("UserRecords")
        
        self.is_initialized = True
        print("System initialized successfully!")
        return True
    
    def process_query(self, user_query: str) -> dict:
        """Process a user query through the complete pipeline"""
        if not self.is_initialized:
            return {"error": "System not initialized. Please run initialize_system first."}
        
        print(f"\nProcessing query: '{user_query}'")
        
        try:
            # Step 1: Use the schema directly (no vector search for simplicity)
            print("\nStep 1: Using UserRecords table schema...")
            relevant_schemas = [self.schema_text]
            
            # Step 2: Generate SQL query
            print("\nStep 2: Generating SQL query...")
            sql_query = self.sql_generator.generate_sql_query(user_query, relevant_schemas)
            
            if not sql_query:
                return {"error": "Failed to generate SQL query"}
            
            print(f"Generated SQL: {sql_query}")
            
            # Step 3: Execute SQL query
            print("\nStep 3: Executing SQL query...")
            success, results, execution_info, attempts = self.sql_executor.execute_query_with_retry(sql_query)
            
            if not success:
                print("Query failed, attempting to improve...")
                improved_query = self.sql_generator.validate_and_improve_query(sql_query, str(results))
                if improved_query != sql_query:
                    print(f"Improved SQL: {improved_query}")
                    success, results, execution_info, attempts = self.sql_executor.execute_query_with_retry(improved_query)
                    sql_query = improved_query
            
            if not success:
                return {
                    "error": f"SQL execution failed: {results}",
                    "sql_query": sql_query,
                    "execution_attempts": attempts
                }
            
            print(f"Query executed successfully! Retrieved {len(results)} rows")
            
            # Step 4: Process results to natural language
            print("\nStep 4: Generating natural language response...")
            final_answer = self.result_processor.process_results_to_text(
                user_query, sql_query, results, execution_info
            )
            
            return {
                "user_query": user_query,
                "sql_query": sql_query,
                "result_count": len(results) if results else 0,
                "sample_results": results[:3] if results else [],
                "final_answer": final_answer,
                "execution_info": execution_info
            }
            
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def interactive_mode(self):
        """Run the system in interactive mode"""
        print("\n" + "="*60)
        print("Quick Text-to-SQL System - Interactive Mode")
        print("="*60)
        print("Enter your questions in natural language.")
        print("Type 'quit' or 'exit' to stop.")
        print("Type 'test' to test database connection.")
        print("Type 'schema' to view the database schema.")
        print("-"*60)
        
        while True:
            try:
                user_input = input("\nYour question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if user_input.lower() == 'test':
                    print("Testing database connection...")
                    if self.sql_executor.test_connection():
                        print("SUCCESS: Database connection successful!")
                    else:
                        print("FAILED: Database connection failed!")
                    continue
                
                if user_input.lower() == 'schema':
                    print("\nDatabase Schema:")
                    print("-" * 40)
                    print(self.schema_text)
                    continue
                
                if not user_input:
                    print("Please enter a question.")
                    continue
                
                # Process the query
                result = self.process_query(user_input)
                
                if "error" in result:
                    print(f"ERROR: {result['error']}")
                    continue
                
                # Display results
                print(f"\n{'='*60}")
                print(f"QUERY: {result['user_query']}")
                print(f"{'='*60}")
                print(f"\nSQL QUERY:")
                print(result['sql_query'])
                print(f"\nEXECUTION INFO:")
                print(result['execution_info'])
                if result['sample_results']:
                    print(f"\nSAMPLE RESULTS:")
                    for i, row in enumerate(result['sample_results'], 1):
                        print(f"Row {i}: {dict(row)}")
                print(f"\nFINAL ANSWER:")
                print(result['final_answer'])
                print(f"{'='*60}")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"ERROR: Unexpected error: {str(e)}")

def main():
    """Main function"""
    system = QuickTextToSQLSystem()
    
    # Check if CSV file path is provided
    csv_file = "enhanced_db_schema.csv"
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"ERROR: CSV file not found: {csv_file}")
        return
    
    # Initialize system
    if not system.initialize_system(csv_file):
        print("Failed to initialize system. Exiting.")
        return
    
    # Test database connection
    print("\nTesting database connection...")
    if not system.sql_executor.test_connection():
        print("WARNING: Database connection failed.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    else:
        print("SUCCESS: Database connection successful!")
    
    # Start interactive mode
    system.interactive_mode()

if __name__ == "__main__":
    main()