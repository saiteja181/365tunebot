#!/usr/bin/env python3
"""
Secure SQL Executor with Tenant Validation
CRITICAL: Validates ALL queries have tenant filtering before execution
"""

import pyodbc
import pandas as pd
import warnings
import time
from typing import List, Dict, Tuple, Any, Optional
from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
from tenant_security import (
    TenantSecurityException,
    TenantValidator,
    audit_logger
)

# Suppress pandas warnings
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

class SecureSQLExecutor:
    """
    Secure SQL Executor with tenant isolation enforcement

    This class provides the FINAL layer of defense by validating that all
    SQL queries contain proper tenant filtering before execution.
    """

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
        self.rls_enabled = False  # Track if RLS is enabled

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

    def execute_query_secure(self, sql_query: str, tenant_code: str,
                             session_id: str = "default",
                             params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any, str]:
        """
        Execute SQL query with tenant security validation using parameterized queries

        Args:
            sql_query: SQL query to execute (with ? placeholders)
            tenant_code: Tenant code for filtering
            session_id: Session ID for audit logging
            params: Optional parameters for parameterized query

        Returns:
            Tuple of (success, results_or_error, execution_info)

        Raises:
            TenantSecurityException: If security validation fails
        """
        start_time = time.time()

        # CRITICAL: Pre-execution security validation
        try:
            self._validate_query_security(sql_query, tenant_code, session_id)
        except TenantSecurityException as e:
            # Log security violation
            audit_logger.log_security_violation(
                session_id, tenant_code,
                'query_validation_failed',
                str(e)
            )

            # Log failed query attempt
            audit_logger.log_query(
                session_id, tenant_code, sql_query,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                security_violation=str(e)
            )

            return False, str(e), f"Security validation failed: {str(e)}"

        # Ensure connection
        if not self.connection:
            if not self.connect():
                return False, None, "Failed to establish database connection"

        try:
            # Set session context for Row-Level Security (if enabled)
            if self.rls_enabled:
                self._set_session_context(tenant_code)

            # Execute query with parameters if provided
            if params:
                # Convert SQL Server @parameter syntax to pyodbc ? syntax
                # params = {"tenant_code_0": "value", "tenant_code_1": "value"}
                # SQL has @tenant_code_0, @tenant_code_1
                # Need to convert to ? and provide values in order

                # Sort params by key to ensure consistent ordering
                sorted_params = sorted(params.items())
                param_values = [value for key, value in sorted_params]

                # Replace @param_name with ? in the SQL
                converted_sql = sql_query
                for param_name, _ in sorted_params:
                    converted_sql = converted_sql.replace(f"@{param_name}", "?", 1)

                # Execute with positional parameters
                cursor = self.connection.cursor()
                cursor.execute(converted_sql, param_values)

                # Fetch results
                columns = [column[0] for column in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                cursor.close()
                df = pd.DataFrame(results)
            else:
                # Fallback to pandas read_sql (for queries without params)
                df = pd.read_sql(sql_query, self.connection)

            # Convert to list of dictionaries
            results = df.to_dict('records')

            execution_time = (time.time() - start_time) * 1000  # milliseconds
            execution_info = f"Query executed successfully. Retrieved {len(results)} rows, {len(df.columns)} columns in {execution_time:.2f}ms"

            # Post-execution validation (verify results are from correct tenant)
            self._validate_result_tenant(results, tenant_code)

            # Log successful query
            audit_logger.log_query(
                session_id, tenant_code, sql_query,
                success=True,
                row_count=len(results),
                execution_time_ms=execution_time
            )

            return True, results, execution_info

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_message = str(e)
            execution_info = f"Query execution failed: {error_message}"

            # Log failed query
            audit_logger.log_query(
                session_id, tenant_code, sql_query,
                success=False,
                execution_time_ms=execution_time
            )

            return False, error_message, execution_info

    def execute_query_with_retry(self, sql_query: str, tenant_code: str,
                                 session_id: str = "default",
                                 max_retries: int = 2,
                                 params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any, str, List[str]]:
        """
        Execute query with retry logic (secure version)

        Args:
            sql_query: SQL query
            tenant_code: Tenant code
            session_id: Session ID
            max_retries: Maximum retry attempts
            params: Optional parameters for parameterized query

        Returns:
            Tuple of (success, results, execution_info, attempts_log)
        """
        attempts = []

        for attempt in range(max_retries + 1):
            success, result, info = self.execute_query_secure(
                sql_query, tenant_code, session_id, params
            )

            attempt_info = f"Attempt {attempt + 1}: {info}"
            attempts.append(attempt_info)

            if success:
                return True, result, info, attempts

            # If last attempt, return error
            if attempt == max_retries:
                return False, result, info, attempts

            print(f"Query failed on attempt {attempt + 1}, retrying...")

        return False, "Max retries exceeded", "Query execution failed", attempts

    def _validate_query_security(self, sql_query: str, tenant_code: str, session_id: str):
        """
        Validate query meets security requirements

        Args:
            sql_query: SQL query to validate
            tenant_code: Expected tenant code
            session_id: Session ID

        Raises:
            TenantSecurityException: If validation fails
        """
        # Validate tenant code
        is_valid, error_msg = TenantValidator.validate_tenant_code(tenant_code)
        if not is_valid:
            raise TenantSecurityException(f"Invalid tenant code: {error_msg}")

        # Validate query has tenant filter
        is_valid, error_msg = TenantValidator.validate_sql_has_tenant_filter(
            sql_query, tenant_code
        )

        if not is_valid:
            raise TenantSecurityException(
                f"Query failed tenant filter validation: {error_msg}"
            )

        # Additional security checks
        self._check_for_security_violations(sql_query)

    def _check_for_security_violations(self, sql_query: str):
        """
        Check for common security violations in SQL

        Args:
            sql_query: SQL query to check

        Raises:
            TenantSecurityException: If security violation detected
        """
        sql_upper = sql_query.upper()

        # Check for dangerous operations
        dangerous_keywords = [
            ('DROP ', 'DROP operations not allowed'),
            ('TRUNCATE ', 'TRUNCATE operations not allowed'),
            ('DELETE ', 'DELETE operations not allowed'),
            ('UPDATE ', 'UPDATE operations not allowed'),
            ('INSERT ', 'INSERT operations not allowed'),
            ('EXEC ', 'EXEC operations not allowed'),
            ('EXECUTE ', 'EXECUTE operations not allowed'),
            ('SP_', 'Stored procedure calls not allowed'),
            ('XP_', 'Extended procedure calls not allowed'),
        ]

        for keyword, message in dangerous_keywords:
            if keyword in sql_upper:
                raise TenantSecurityException(message)

        # Check for SQL injection patterns
        injection_patterns = [
            (r';\s*DROP', 'SQL injection attempt detected: DROP'),
            (r';\s*DELETE', 'SQL injection attempt detected: DELETE'),
            (r';\s*UPDATE', 'SQL injection attempt detected: UPDATE'),
            (r'/\*.*?\*/', 'SQL comments not allowed'),
            (r'--.*$', 'SQL comments not allowed'),
        ]

        import re
        for pattern, message in injection_patterns:
            if re.search(pattern, sql_query, re.IGNORECASE | re.MULTILINE):
                raise TenantSecurityException(message)

    def _validate_result_tenant(self, results: List[Dict], tenant_code: str):
        """
        Validate that returned results belong to the correct tenant

        Args:
            results: Query results
            tenant_code: Expected tenant code

        Raises:
            TenantSecurityException: If results contain wrong tenant data
        """
        if not results:
            return  # No results to validate

        # Check if results have TenantCode column
        if 'TenantCode' in results[0]:
            for row in results:
                if row.get('TenantCode') != tenant_code:
                    raise TenantSecurityException(
                        f"CRITICAL: Result contains data from different tenant! "
                        f"Expected: {tenant_code}, Found: {row.get('TenantCode')}"
                    )

    def _set_session_context(self, tenant_code: str):
        """
        Set session context for Row-Level Security

        Args:
            tenant_code: Tenant code to set in session context
        """
        try:
            context_sql = "EXEC sp_set_session_context @key = N'TenantCode', @value = ?"
            cursor = self.connection.cursor()
            cursor.execute(context_sql, tenant_code)
            cursor.close()
        except Exception as e:
            print(f"Warning: Failed to set session context for RLS: {str(e)}")

    def enable_rls(self):
        """Enable Row-Level Security mode"""
        self.rls_enabled = True
        print("Row-Level Security mode enabled")

    def disable_rls(self):
        """Disable Row-Level Security mode"""
        self.rls_enabled = False
        print("Row-Level Security mode disabled")

    def test_connection(self) -> bool:
        """Test database connection"""
        test_query = "SELECT 1 as test_value"
        try:
            if not self.connection:
                if not self.connect():
                    return False

            cursor = self.connection.cursor()
            cursor.execute(test_query)
            cursor.close()
            return True
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False

    def get_table_info(self, table_name: str) -> Dict:
        """Get table information (without security validation - for admin use)"""
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

        try:
            if not self.connection:
                self.connect()

            df = pd.read_sql(info_query, self.connection)
            results = df.to_dict('records')

            return {
                'table_name': table_name,
                'columns': results,
                'column_count': len(results)
            }
        except Exception as e:
            return {'table_name': table_name, 'error': str(e)}

    def format_results_for_display(self, results: List[Dict], max_rows: int = 10) -> str:
        """Format results for display"""
        if not results:
            return "No results returned"

        display_results = results[:max_rows]

        if len(results) > max_rows:
            truncated_note = f"\n... (showing first {max_rows} of {len(results)} rows)"
        else:
            truncated_note = f"\n(Total: {len(results)} rows)"

        df = pd.DataFrame(display_results)
        return df.to_string(index=False) + truncated_note


# Maintain compatibility with existing code
class SQLExecutor(SecureSQLExecutor):
    """
    Backward compatible SQL Executor (now secure by default)

    NOTE: This wraps SecureSQLExecutor to maintain compatibility with existing code.
    All execute_query calls now require tenant_code parameter.
    """

    def execute_query(self, sql_query: str, tenant_code: str = None,
                     session_id: str = "default") -> Tuple[bool, Any, str]:
        """
        Execute query (backward compatible interface)

        Args:
            sql_query: SQL query
            tenant_code: Tenant code (REQUIRED for security)
            session_id: Session ID

        Returns:
            Tuple of (success, results_or_error, execution_info)
        """
        if tenant_code is None:
            # CRITICAL: For backward compatibility, try to extract tenant from query
            # In production, this should raise an exception
            print("WARNING: execute_query called without tenant_code - security risk!")
            return False, "tenant_code is required", "Security: tenant_code parameter is mandatory"

        return self.execute_query_secure(sql_query, tenant_code, session_id)

    def execute_query_with_retry(self, sql_query: str, tenant_code: str = None,
                                 session_id: str = "default",
                                 max_retries: int = 2,
                                 params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any, str, List[str]]:
        """Execute query with retry (backward compatible)"""
        if tenant_code is None:
            print("WARNING: execute_query_with_retry called without tenant_code!")
            return False, "tenant_code is required", "Security: tenant_code required", []

        return super().execute_query_with_retry(sql_query, tenant_code, session_id, max_retries, params)
