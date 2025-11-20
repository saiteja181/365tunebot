#!/usr/bin/env python3
"""
Multi-Tenant Security Module
Provides authentication, validation, and security utilities for tenant isolation
"""

import re
import hashlib
import secrets
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import threading

# Thread-safe storage for tenant sessions
tenant_sessions = {}
session_lock = threading.Lock()

# Allowed tenant codes - in production, load from database
ALLOWED_TENANTS = set()  # Will be populated from database

class TenantSecurityException(Exception):
    """Raised when tenant security validation fails"""
    pass

class TenantAuthenticator:
    """Handles tenant authentication and session management"""

    def __init__(self):
        self.session_timeout_minutes = 60

    def authenticate(self, username: str, password: str, tenant_code: str) -> Dict[str, Any]:
        """
        Authenticate user with tenant code

        Args:
            username: User's email or username
            password: User's password
            tenant_code: Organization's tenant code

        Returns:
            Dict with authentication result and session info

        Raises:
            TenantSecurityException: If authentication fails
        """
        # Validate tenant code format (prevent injection)
        if not self._is_valid_tenant_code(tenant_code):
            raise TenantSecurityException("Invalid tenant code format")

        # TODO: Validate against database
        # For now, we'll create a session if tenant code is valid

        # Generate secure session ID
        session_id = self._generate_session_id()

        # Create session with tenant context
        session_data = {
            'session_id': session_id,
            'tenant_code': tenant_code,
            'username': username,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'ip_address': None,  # Set by middleware
            'authenticated': True
        }

        # Store session
        with session_lock:
            tenant_sessions[session_id] = session_data

        return {
            'success': True,
            'session_id': session_id,
            'tenant_code': tenant_code,
            'message': 'Authentication successful'
        }

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate session and return tenant context

        Args:
            session_id: Session ID to validate

        Returns:
            Session data if valid, None otherwise
        """
        with session_lock:
            session = tenant_sessions.get(session_id)

            if not session:
                return None

            # Check session timeout
            timeout = timedelta(minutes=self.session_timeout_minutes)
            if datetime.now() - session['last_activity'] > timeout:
                del tenant_sessions[session_id]
                return None

            # Update last activity
            session['last_activity'] = datetime.now()

            return session

    def get_tenant_from_session(self, session_id: str) -> Optional[str]:
        """
        Get tenant code from session

        Args:
            session_id: Session ID

        Returns:
            Tenant code or None
        """
        session = self.validate_session(session_id)
        return session['tenant_code'] if session else None

    def logout(self, session_id: str) -> bool:
        """
        Logout and invalidate session

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if session was found and removed
        """
        with session_lock:
            if session_id in tenant_sessions:
                del tenant_sessions[session_id]
                return True
            return False

    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)

    def _is_valid_tenant_code(self, tenant_code: str) -> bool:
        """
        Validate tenant code format

        Args:
            tenant_code: Tenant code to validate

        Returns:
            True if valid format
        """
        # Only allow alphanumeric and underscores, 3-50 characters
        if not tenant_code or not isinstance(tenant_code, str):
            return False

        if len(tenant_code) < 3 or len(tenant_code) > 50:
            return False

        # Accept two formats:
        # 1. Alphanumeric with underscores (e.g., ACME_CORP)
        # 2. GUID format (e.g., 6c657194-e896-4367-a285-478e3ef159b6)
        is_alphanumeric = re.match(r'^[A-Za-z0-9_]+$', tenant_code)
        is_guid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', tenant_code, re.IGNORECASE)

        if not (is_alphanumeric or is_guid):
            return False

        return True

class TenantValidator:
    """Validates tenant access in queries and requests"""

    @staticmethod
    def validate_tenant_code(tenant_code: str) -> Tuple[bool, str]:
        """
        Validate tenant code

        Args:
            tenant_code: Tenant code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not tenant_code:
            return False, "Tenant code is required"

        if not isinstance(tenant_code, str):
            return False, "Tenant code must be a string"

        if len(tenant_code) < 3 or len(tenant_code) > 50:
            return False, "Tenant code must be 3-50 characters"

        # Accept two formats:
        # 1. Alphanumeric with underscores (e.g., ACME_CORP)
        # 2. GUID format (e.g., 6c657194-e896-4367-a285-478e3ef159b6)
        is_alphanumeric = re.match(r'^[A-Za-z0-9_]+$', tenant_code)
        is_guid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', tenant_code, re.IGNORECASE)

        if not (is_alphanumeric or is_guid):
            return False, "Tenant code must be alphanumeric/underscore or valid GUID format"

        return True, ""

    @staticmethod
    def validate_sql_has_tenant_filter(sql_query: str, tenant_code: str) -> Tuple[bool, str]:
        """
        Validate that SQL query contains tenant filter

        Args:
            sql_query: SQL query to validate
            tenant_code: Expected tenant code in filter

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql_query:
            return False, "SQL query is empty"

        # Convert to uppercase for case-insensitive search
        sql_upper = sql_query.upper()

        # Check if query references tables that need tenant filtering
        tables_needing_filter = ['USERRECORDS', 'LICENSES']
        query_has_tenant_table = any(table in sql_upper for table in tables_needing_filter)

        if not query_has_tenant_table:
            # Query doesn't use tenant tables, no filter needed
            return True, ""

        # Check for WHERE clause with TenantCode
        if 'WHERE' not in sql_upper:
            return False, "Query missing WHERE clause for tenant filtering"

        # Check for TenantCode in WHERE clause
        if 'TENANTCODE' not in sql_upper:
            return False, "Query missing TenantCode filter"

        # Check for parameterized query (? or @param)
        # Or check for specific tenant code value
        has_param = '?' in sql_query or '@' in sql_query
        has_tenant_value = tenant_code.upper() in sql_upper

        if not (has_param or has_tenant_value):
            return False, "Query missing tenant code parameter or value"

        # Additional security: Check for SQL injection attempts
        suspicious_patterns = [
            r'OR\s+1\s*=\s*1',  # OR 1=1 injection
            r'OR\s+\'\s*\'\s*=\s*\'',  # OR ''='' injection
            r'--',  # SQL comments
            r'/\*',  # Multi-line comments
            r';\s*DROP',  # DROP statements
            r';\s*DELETE',  # DELETE statements
            r';\s*UPDATE',  # UPDATE statements
            r'UNION\s+SELECT',  # UNION injection
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, sql_upper):
                return False, f"Suspicious SQL pattern detected: {pattern}"

        return True, ""

    @staticmethod
    def sanitize_tenant_code(tenant_code: str) -> str:
        """
        Sanitize tenant code for safe use in SQL

        Args:
            tenant_code: Tenant code to sanitize

        Returns:
            Sanitized tenant code
        """
        # Remove any characters that aren't alphanumeric, underscore, or hyphen (for GUIDs)
        return re.sub(r'[^A-Za-z0-9_-]', '', tenant_code)

class TenantAuditLogger:
    """Logs all tenant-related operations for security auditing"""

    def __init__(self, log_file: str = "tenant_security_audit.log"):
        self.log_file = log_file
        self.log_lock = threading.Lock()

    def log_query(self, session_id: str, tenant_code: str, sql_query: str,
                  success: bool, row_count: int = 0, execution_time_ms: float = 0,
                  security_violation: str = None):
        """
        Log SQL query execution with tenant context

        Args:
            session_id: Session ID
            tenant_code: Tenant code
            sql_query: SQL query executed
            success: Whether query succeeded
            row_count: Number of rows returned
            execution_time_ms: Execution time in milliseconds
            security_violation: Security violation message if any
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'tenant_code': tenant_code,
            'sql_query': sql_query[:500],  # Limit length
            'success': success,
            'row_count': row_count,
            'execution_time_ms': execution_time_ms,
            'security_violation': security_violation
        }

        with self.log_lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')

    def log_authentication(self, username: str, tenant_code: str, success: bool,
                          ip_address: str = None, reason: str = None):
        """
        Log authentication attempt

        Args:
            username: Username attempting auth
            tenant_code: Tenant code
            success: Whether auth succeeded
            ip_address: IP address of request
            reason: Reason for failure if not successful
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'authentication',
            'username': username,
            'tenant_code': tenant_code,
            'success': success,
            'ip_address': ip_address,
            'reason': reason
        }

        with self.log_lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')

    def log_security_violation(self, session_id: str, tenant_code: str,
                              violation_type: str, details: str):
        """
        Log security violation

        Args:
            session_id: Session ID
            tenant_code: Tenant code
            violation_type: Type of violation
            details: Violation details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'security_violation',
            'session_id': session_id,
            'tenant_code': tenant_code,
            'violation_type': violation_type,
            'details': details
        }

        with self.log_lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')

        # Also print to console for immediate visibility
        print(f"[SECURITY VIOLATION] {violation_type}: {details}")

class TenantSecurityMonitor:
    """Monitors and detects suspicious tenant access patterns"""

    def __init__(self, audit_logger: TenantAuditLogger):
        self.audit_logger = audit_logger
        self.failed_attempts = {}  # Track failed attempts per session
        self.max_failures = 5

    def track_failure(self, session_id: str, tenant_code: str, reason: str) -> bool:
        """
        Track failed attempt and detect suspicious behavior

        Args:
            session_id: Session ID
            tenant_code: Tenant code
            reason: Reason for failure

        Returns:
            True if threshold exceeded (potential attack)
        """
        key = f"{session_id}_{tenant_code}"

        if key not in self.failed_attempts:
            self.failed_attempts[key] = []

        self.failed_attempts[key].append({
            'timestamp': datetime.now(),
            'reason': reason
        })

        # Check if threshold exceeded
        if len(self.failed_attempts[key]) >= self.max_failures:
            self.audit_logger.log_security_violation(
                session_id, tenant_code,
                'excessive_failures',
                f'Session exceeded {self.max_failures} failures: {reason}'
            )
            return True

        return False

    def reset_failures(self, session_id: str, tenant_code: str):
        """Reset failure counter for session"""
        key = f"{session_id}_{tenant_code}"
        if key in self.failed_attempts:
            del self.failed_attempts[key]

# Global instances
audit_logger = TenantAuditLogger()
security_monitor = TenantSecurityMonitor(audit_logger)
tenant_authenticator = TenantAuthenticator()
tenant_validator = TenantValidator()
