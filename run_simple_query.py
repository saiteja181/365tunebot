#!/usr/bin/env python3
"""
Run a simple query to demonstrate the step-by-step output
"""

import os
from main import TextToSQLSystem

def run_simple_query():
    print("=" * 60)
    print("Text-to-SQL System - Simple Query Demo")
    print("=" * 60)
    
    # Initialize system
    system = TextToSQLSystem()
    csv_file = "enhanced_db_schema.csv"
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return
    
    print("Initializing system...")
    success = system.initialize_system(csv_file)
    
    if not success:
        print("Failed to initialize system")
        return
    
    print("System initialized successfully!")
    
    # Test database connection
    print("Testing database connection...")
    if system.sql_executor.test_connection():
        print("Database connection successful!")
    else:
        print("Warning: Database connection failed")
    
    # Run a test query
    test_query = "show all users with active status"
    print(f"\nRunning test query: '{test_query}'")
    print("=" * 60)
    
    result = system.process_query(test_query)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        # Display the formatted results
        formatted_output = system.result_processor.format_response_for_display(result)
        print(formatted_output)

if __name__ == "__main__":
    run_simple_query()