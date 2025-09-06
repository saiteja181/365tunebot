#!/usr/bin/env python3
"""
Sample query test
"""

from quick_app import QuickTextToSQLSystem

def run_sample_query():
    print("Running sample query...")
    
    # Initialize system
    system = QuickTextToSQLSystem()
    
    if not system.initialize_system("enhanced_db_schema.csv"):
        print("Failed to initialize system")
        return
    
    # Test a simple query
    query = "How many users are there in the database?"
    print(f"\nQuery: {query}")
    
    result = system.process_query(query)
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"\nGenerated SQL: {result['sql_query']}")
        print(f"Execution Info: {result['execution_info']}")
        print(f"Result Count: {result['result_count']}")
        if result['sample_results']:
            print(f"Sample Results: {result['sample_results']}")
        print(f"\nFinal Answer: {result['final_answer']}")

if __name__ == "__main__":
    run_sample_query()