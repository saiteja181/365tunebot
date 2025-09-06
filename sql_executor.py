import pyodbc
import pandas as pd
import warnings
from typing import List, Dict, Tuple, Any
from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD

# Suppress the pandas DBAPI2 warning
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

class SQLExecutor:
    def __init__(self):
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection to SQL Server"""
        try:
            self.connection = pyodbc.connect(self.connection_string)
            print("Connected to SQL Server successfully")
            return True
        except Exception as e:
            print(f"Failed to connect to SQL Server: {str(e)}")
            return False
    
    def disconnect(self):
        """Close connection to SQL Server"""
        if self.connection:
            self.connection.close()
            print("Disconnected from SQL Server")
    
    def execute_query(self, sql_query: str) -> Tuple[bool, Any, str]:
        """
        Execute SQL query and return results
        Returns: (success: bool, results: List[Dict] or error_message: str, execution_info: str)
        """
        if not self.connection:
            if not self.connect():
                return False, None, "Failed to establish database connection"
        
        try:
            # Use pandas to execute query and get results as DataFrame
            df = pd.read_sql(sql_query, self.connection)
            
            # Convert DataFrame to list of dictionaries for easier handling
            results = df.to_dict('records')
            
            execution_info = f"Query executed successfully. Retrieved {len(results)} rows, {len(df.columns)} columns."
            
            return True, results, execution_info
            
        except Exception as e:
            error_message = str(e)
            execution_info = f"Query execution failed: {error_message}"
            return False, error_message, execution_info
    
    def execute_query_with_retry(self, sql_query: str, max_retries: int = 2) -> Tuple[bool, Any, str, List[str]]:
        """
        Execute SQL query with retry logic for common errors
        Returns: (success: bool, results: Any, final_execution_info: str, all_attempts: List[str])
        """
        attempts = []
        
        for attempt in range(max_retries + 1):
            success, result, info = self.execute_query(sql_query)
            attempt_info = f"Attempt {attempt + 1}: {info}"
            attempts.append(attempt_info)
            
            if success:
                return True, result, info, attempts
            
            # If it's the last attempt, return the error
            if attempt == max_retries:
                return False, result, info, attempts
            
            print(f"Query failed on attempt {attempt + 1}, retrying...")
        
        return False, "Max retries exceeded", "Query execution failed", attempts
    
    def get_table_info(self, table_name: str) -> Dict:
        """Get detailed information about a table"""
        info_query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        
        success, results, info = self.execute_query(info_query)
        
        if success:
            return {
                'table_name': table_name,
                'columns': results,
                'column_count': len(results)
            }
        else:
            return {'table_name': table_name, 'error': results}
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        test_query = "SELECT 1 as test_value"
        success, result, info = self.execute_query(test_query)
        return success
    
    def format_results_for_display(self, results: List[Dict], max_rows: int = 10) -> str:
        """Format query results for readable display"""
        if not results:
            return "No results returned"
        
        # Limit rows for display
        display_results = results[:max_rows]
        
        if len(results) > max_rows:
            truncated_note = f"\n... (showing first {max_rows} of {len(results)} rows)"
        else:
            truncated_note = f"\n(Total: {len(results)} rows)"
        
        # Convert to DataFrame for nice formatting
        df = pd.DataFrame(display_results)
        return df.to_string(index=False) + truncated_note