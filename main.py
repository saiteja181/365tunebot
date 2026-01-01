#!/usr/bin/env python3
"""
Text-to-SQL System with Vector Database Retrieval
"""

import os
import sys
from typing import Optional

from schema_processor import SchemaProcessor
from vector_db import VectorDatabase
from secure_sql_generator import SecureSQLQueryGenerator  # CHANGED for tenant security
from secure_sql_executor import SecureSQLExecutor  # CHANGED for tenant security
from result_processor import ResultProcessor
from direct_answer_system import DirectAnswerSystem
from ai_insights_generator import AIInsightsGenerator
from tenant_security import TenantSecurityException  # NEW for tenant security

class TextToSQLSystem:
    def __init__(self):
        self.schema_processor = SchemaProcessor("")
        self.vector_db = VectorDatabase()
        self.sql_generator = SecureSQLQueryGenerator()  # CHANGED
        self.sql_executor = SecureSQLExecutor()  # CHANGED
        self.result_processor = ResultProcessor()
        self.direct_answer_system = DirectAnswerSystem()
        self.insights_generator = AIInsightsGenerator()
        self.is_initialized = False
    
    def initialize_system(self, csv_file_path: str, force_rebuild: bool = False):
        """Initialize the system with schema data"""
        print("Initializing Text-to-SQL System...")
        
        # Check if we can load existing processed data
        schema_file = "data/processed_schemas.json"
        index_file = "data/faiss_index.idx"
        metadata_file = "data/faiss_metadata.pkl"
        
        if not force_rebuild and all(os.path.exists(f) for f in [schema_file, index_file, metadata_file]):
            print("Loading existing processed data...")
            try:
                self.schema_processor.load_processed_data(schema_file)
                self.vector_db.load_index(index_file, metadata_file)
                # Link direct answer system with schema processor
                self.direct_answer_system.schema_processor = self.schema_processor
                self.is_initialized = True
                print("System initialized successfully from cached data!")
                return True
            except Exception as e:
                print(f"Failed to load cached data: {e}")
                print("Rebuilding from scratch...")
        
        # Process schema from CSV
        print(f"Processing schema from CSV: {csv_file_path}")
        self.schema_processor = SchemaProcessor(csv_file_path)
        schema_data = self.schema_processor.process_csv_schema()
        
        if not schema_data:
            print("Failed to process schema data!")
            return False
        
        # Create vector database
        print("Building vector database...")
        embeddings = self.vector_db.create_embeddings(schema_data)
        self.vector_db.build_faiss_index(embeddings)
        
        # Save processed data for future use
        self.schema_processor.save_processed_data(schema_file)
        self.vector_db.save_index(index_file, metadata_file)

        # Link direct answer system with schema processor
        self.direct_answer_system.schema_processor = self.schema_processor

        self.is_initialized = True
        print("System initialized successfully!")
        return True
    
    def process_query(self, user_query: str, conversation_context: str = "", session_id: str = "default", tenant_code: str = None) -> dict:
        """Process a user query through the complete pipeline with tenant isolation"""
        if not self.is_initialized:
            return {"error": "System not initialized. Please run initialize_system first."}

        # TENANT SECURITY: Require tenant_code
        if not tenant_code:
            return {"error": "tenant_code is required for security"}

        print(f"\nProcessing query: '{user_query}' [Session: {session_id}]")
        
        try:
            # Step 1: Vector search for relevant tables
            print("\nStep 1: Searching for relevant tables...")
            faiss_results = self.vector_db.get_search_results_with_scores(user_query, top_k=3)
            relevant_tables = self.vector_db.get_relevant_tables(user_query, top_k=3)
            
            print(f"Found {len(relevant_tables)} relevant tables: {', '.join(relevant_tables)}")
            
            # Show detailed FAISS results
            print("Vector search results:")
            for i, result in enumerate(faiss_results, 1):
                table_name = result.get('table_name', 'unknown')
                score = result.get('relevance_score', 0)
                preview = result.get('schema_preview', 'No preview available')
                print(f"  {i}. {table_name} (relevance: {score:.3f})")
                print(f"     Schema: {preview}")
            
            # Get detailed schema for relevant tables
            relevant_schemas = []
            for table_name in relevant_tables:
                schema_text = self.schema_processor.get_table_schema_text(table_name)
                relevant_schemas.append(schema_text)
            
            # Step 2: Generate SQL query (using conversation history for speed)
            print("\nStep 2: Generating SQL query...")
            if conversation_context:
                print(f"Using conversation context: {conversation_context[:100]}...")

            # Use optimized generation with conversation history and TENANT SECURITY
            sql_query, params = self.sql_generator.generate_sql_query_secure(
                user_query, relevant_schemas, tenant_code, conversation_context, session_id=session_id
            )

            if not sql_query:
                return {"error": "Failed to generate SQL query"}

            print(f"Generated SQL: {sql_query}")
            print(f"Query length: {len(sql_query)} characters")
            
            # Step 3: Execute SQL query with TENANT SECURITY
            print("\nStep 3: Executing SQL query...")
            success, results, execution_info, attempts = self.sql_executor.execute_query_with_retry(sql_query, tenant_code, session_id, params=params)
            
            if not success:
                # Try to improve the query based on the error
                print("Query failed, attempting to improve...")
                schema_context = "\n\n".join(relevant_schemas)
                improved_query = self.sql_generator.validate_and_improve_query(sql_query, str(results), schema_context)
                if improved_query != sql_query:
                    print(f"Improved SQL: {improved_query}")
                    success, results, execution_info, attempts = self.sql_executor.execute_query_with_retry(
                        improved_query, tenant_code, session_id
                    )
                    sql_query = improved_query  # Update for final response
                
                # If still failing and we used context, try without context as fallback
                if not success and conversation_context:
                    print("Context-based query failed, trying without context as fallback...")
                    fallback_query = self.sql_generator.generate_sql_query_secure(
                        user_query, relevant_schemas, tenant_code, ""
                    )
                    if fallback_query != sql_query:
                        print(f"Fallback SQL: {fallback_query}")
                        success, results, execution_info, attempts = self.sql_executor.execute_query_with_retry(
                            fallback_query, tenant_code, session_id
                        )
                        if success:
                            sql_query = fallback_query  # Update for final response
            
            if not success:
                return {
                    "error": f"SQL execution failed: {results}",
                    "faiss_results": faiss_results,
                    "sql_query": sql_query,
                    "execution_attempts": attempts
                }
            
            print(f"Query executed successfully! Retrieved {len(results)} rows")
            print(f"Execution info: {execution_info}")
            
            # Show sample results
            if results:
                print("Sample results (first 3 rows):")
                for i, row in enumerate(results[:3], 1):
                    print(f"  Row {i}: {dict(row)}")
            
            # Step 4: Process results to natural language
            print("\nStep 4: Generating natural language response...")
            final_answer = self.result_processor.process_results_to_text(
                user_query, sql_query, results, execution_info
            )
            
            # Create comprehensive response
            summary = self.result_processor.create_summary_response(
                user_query, faiss_results, sql_query, results, final_answer, execution_info
            )
            
            return summary
            
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def interactive_mode(self):
        """Run the system in interactive mode"""
        print("\n" + "="*60)
        print("Text-to-SQL System - Interactive Mode")
        print("="*60)
        print("Enter your questions in natural language.")
        print("Type 'quit' or 'exit' to stop.")
        print("Type 'test' to test database connection.")
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
                        print("Database connection successful!")
                    else:
                        print("Database connection failed!")
                    continue
                
                if not user_input:
                    print("Please enter a question.")
                    continue
                
                # Process the query
                result = self.process_query(user_input)
                
                if "error" in result:
                    print(f"Error: {result['error']}")
                    continue
                
                # Display results
                formatted_output = self.result_processor.format_response_for_display(result)
                print(formatted_output)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Unexpected error: {str(e)}")

def main():
    """Main function"""
    system = TextToSQLSystem()
    
    # Check if CSV file path is provided
    csv_file = "schema_data.csv"  # Default CSV file name
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        print("Please ensure you have a CSV file with columns: table_name, column_name, data_type, description")
        print(f"Usage: python {sys.argv[0]} [csv_file_path]")
        return
    
    # Initialize system
    if not system.initialize_system(csv_file):
        print("Failed to initialize system. Exiting.")
        return
    
    # Test database connection
    print("\nTesting database connection...")
    if not system.sql_executor.test_connection():
        print("Warning: Database connection failed. Please check your connection settings in config.py")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    else:
        print("Database connection successful!")
    
    # Start interactive mode
    system.interactive_mode()

if __name__ == "__main__":
    main()