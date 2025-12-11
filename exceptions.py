"""
Custom exceptions for Elevare application.
All business logic and API errors should use these exception classes.
"""

from typing import Any, Optional, Dict
from fastapi import status


class ElevareException(Exception):
    """Base exception for all Elevare errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ==========================================
# VALIDATION ERRORS (400)
# ==========================================

class ValidationError(ElevareException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class InvalidIdeaError(ValidationError):
    """Raised when idea validation fails."""
    pass


class InvalidUserInputError(ValidationError):
    """Raised when user input is invalid."""
    pass


# ==========================================
# AUTHENTICATION & AUTHORIZATION ERRORS (401, 403)
# ==========================================

class AuthenticationError(ElevareException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(ElevareException):
    """Raised when user doesn't have permission."""
    
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    pass


# ==========================================
# NOT FOUND ERRORS (404)
# ==========================================

class NotFoundError(ElevareException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class IdeaNotFoundError(NotFoundError):
    """Raised when an idea is not found."""
    
    def __init__(self, idea_id: Any):
        super().__init__(
            message=f"Idea not found",
            resource_type="idea",
            resource_id=str(idea_id)
        )


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found."""
    
    def __init__(self, user_id: Any):
        super().__init__(
            message=f"User not found",
            resource_type="user",
            resource_id=str(user_id)
        )


class TeamNotFoundError(NotFoundError):
    """Raised when a team is not found."""
    
    def __init__(self, team_id: str):
        super().__init__(
            message=f"Team not found",
            resource_type="team",
            resource_id=team_id
        )


# ==========================================
# CONFLICT ERRORS (409)
# ==========================================

class ConflictError(ElevareException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class DuplicateResourceError(ConflictError):
    """Raised when trying to create a duplicate resource."""
    pass


# ==========================================
# RATE LIMITING (429)
# ==========================================

class RateLimitError(ElevareException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# ==========================================
# EXTERNAL SERVICE ERRORS (502, 503, 504)
# ==========================================

class ExternalServiceError(ElevareException):
    """Raised when an external service fails."""
    
    def __init__(self, service_name: str, message: Optional[str] = None, original_error: Optional[Exception] = None):
        error_msg = message or f"External service '{service_name}' is unavailable"
        details = {"service": service_name}
        
        if original_error:
            details["original_error"] = str(original_error)
        
        super().__init__(
            message=error_msg,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class GroqAPIError(ExternalServiceError):
    """Raised when Groq API fails."""
    
    def __init__(self, message: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(
            service_name="Groq API",
            message=message,
            original_error=original_error
        )


class GitHubAPIError(ExternalServiceError):
    """Raised when GitHub API fails."""
    
    def __init__(self, message: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(
            service_name="GitHub API",
            message=message,
            original_error=original_error
        )


class DatabaseError(ExternalServiceError):
    """Raised when database operations fail."""
    
    def __init__(self, message: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(
            service_name="Database",
            message=message or "Database operation failed",
            original_error=original_error
        )


class RedisError(ExternalServiceError):
    """Raised when Redis operations fail."""
    
    def __init__(self, message: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(
            service_name="Redis",
            message=message or "Redis operation failed",
            original_error=original_error
        )


# ==========================================
# BUSINESS LOGIC ERRORS (422)
# ==========================================

class BusinessLogicError(ElevareException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class InsufficientDataError(BusinessLogicError):
    """Raised when there's not enough data to perform an operation."""
    pass


class MatchingError(BusinessLogicError):
    """Raised when cofounder matching fails."""
    pass


# ==========================================
# INTERNAL SERVER ERRORS (500)
# ==========================================

class InternalServerError(ElevareException):
    """Raised for unexpected internal errors."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ConfigurationError(InternalServerError):
    """Raised when there's a configuration error."""
    pass


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def error_response(exception: ElevareException) -> dict:
    """Convert an exception to a JSON-serializable error response."""
    return {
        "error": {
            "message": exception.message,
            "status_code": exception.status_code,
            "details": exception.details
        },
        "detail": exception.message
    }
