#!/usr/bin/env python3
"""
Centralized Error Handling
Provides custom exceptions and error response formatting
"""

from typing import Optional, Dict, Any
from enum import Enum
from logger_config import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories for better error handling"""
    VALIDATION = "validation_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    DATABASE = "database_error"
    EXTERNAL_API = "external_api_error"
    BUSINESS_LOGIC = "business_logic_error"
    SYSTEM = "system_error"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit_error"


class ApplicationError(Exception):
    """Base application error with categorization"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        http_status: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.user_message = user_message or self._get_default_user_message()
        self.details = details or {}
        self.http_status = http_status

    def _get_default_user_message(self) -> str:
        """Get user-friendly message based on category"""
        messages = {
            ErrorCategory.VALIDATION: "The information provided is invalid. Please check your input.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.DATABASE: "We're having trouble accessing the database. Please try again.",
            ErrorCategory.EXTERNAL_API: "We're having trouble connecting to external services. Please try again.",
            ErrorCategory.BUSINESS_LOGIC: "Unable to process your request due to business rules.",
            ErrorCategory.SYSTEM: "An unexpected error occurred. Please try again later.",
            ErrorCategory.NOT_FOUND: "The requested resource was not found.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please slow down."
        }
        return messages.get(self.category, "An error occurred.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API response"""
        return {
            "success": False,
            "error": {
                "category": self.category.value,
                "message": self.user_message,
                "details": self.details
            }
        }

    def log(self):
        """Log the error with appropriate level"""
        log_data = {
            "category": self.category.value,
            "user_message": self.user_message,
            "details": self.details
        }

        if self.category in [ErrorCategory.SYSTEM, ErrorCategory.DATABASE]:
            logger.error(self.message, **log_data)
        else:
            logger.warning(self.message, **log_data)


class ValidationError(ApplicationError):
    """Input validation error"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            details=details,
            http_status=400,
            **kwargs
        )


class AuthenticationError(ApplicationError):
    """Authentication error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            http_status=401,
            **kwargs
        )


class AuthorizationError(ApplicationError):
    """Authorization error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            http_status=403,
            **kwargs
        )


class DatabaseError(ApplicationError):
    """Database operation error"""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if query:
            details["query"] = query[:200]  # Limit query length
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            details=details,
            http_status=500,
            **kwargs
        )


class ExternalAPIError(ApplicationError):
    """External API error"""

    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if service:
            details["service"] = service
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_API,
            details=details,
            http_status=502,
            **kwargs
        )


class NotFoundError(ApplicationError):
    """Resource not found error"""

    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(
            message=message,
            category=ErrorCategory.NOT_FOUND,
            details=details,
            http_status=404,
            **kwargs
        )


class RateLimitError(ApplicationError):
    """Rate limit exceeded error"""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            details=details,
            http_status=429,
            **kwargs
        )


class SQLGenerationError(ApplicationError):
    """SQL query generation error"""

    def __init__(self, message: str, user_query: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if user_query:
            details["user_query"] = user_query
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            user_message="I couldn't generate a valid SQL query for your request. Please try rephrasing your question.",
            details=details,
            http_status=400,
            **kwargs
        )


class QueryExecutionError(ApplicationError):
    """SQL query execution error"""

    def __init__(self, message: str, sql_query: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if sql_query:
            details["sql_query"] = sql_query[:200]
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            user_message="There was an error executing your query. Please try a different question.",
            details=details,
            http_status=500,
            **kwargs
        )


def handle_exception(e: Exception) -> ApplicationError:
    """
    Convert generic exceptions to ApplicationError

    Args:
        e: Exception to convert

    Returns:
        ApplicationError instance
    """
    if isinstance(e, ApplicationError):
        return e

    # Map common exceptions
    error_message = str(e)

    if "timeout" in error_message.lower():
        return ExternalAPIError(
            message=f"Operation timeout: {error_message}",
            user_message="The operation took too long. Please try again."
        )

    if "connection" in error_message.lower():
        return DatabaseError(
            message=f"Connection error: {error_message}",
            user_message="Unable to connect to the database. Please try again."
        )

    # Default to system error
    return ApplicationError(
        message=f"Unexpected error: {error_message}",
        category=ErrorCategory.SYSTEM
    )
