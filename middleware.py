"""
Middleware for Elevare application.
Handles CORS, request logging, error handling, rate limiting, and security headers.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from config import settings
from logger import get_logger
from exceptions import ElevareException, error_response, RateLimitError

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and outgoing responses.
    Adds request ID for tracking.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed",
                exc_info=exc,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            # Re-raise to be handled by error handler
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catch and handle all exceptions globally.
    Converts exceptions to proper JSON responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except ElevareException as exc:
            # Handle our custom exceptions
            request_id = getattr(request.state, "request_id", None)
            
            response_data = error_response(exc)
            if request_id:
                response_data["request_id"] = request_id
            
            return JSONResponse(
                status_code=exc.status_code,
                content=response_data
            )
        except Exception as exc:
            # Handle unexpected exceptions
            request_id = getattr(request.state, "request_id", None)
            
            logger.error(
                "Unhandled exception",
                exc_info=exc,
                extra={"request_id": request_id}
            )
            
            # Don't expose internal error details in production
            error_message = str(exc) if settings.DEBUG else "Internal server error"
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "message": error_message,
                        "status_code": 500,
                        "request_id": request_id
                    }
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Implements OWASP recommended security headers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        if settings.is_production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
                "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self'"
            )
        
        # HSTS (only in production with HTTPS)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests = {}  # {ip: [(timestamp, count), ...]}
        self.window = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/healthz", "/health", "/metrics"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current time
        current_time = time.time()
        
        # Clean old entries
        self._clean_old_entries(current_time)
        
        # Get request count for this IP
        ip_requests = self.requests.get(client_ip, [])
        
        # Count requests in current window
        recent_requests = [
            ts for ts in ip_requests
            if current_time - ts < self.window
        ]
        
        # Check rate limit
        if len(recent_requests) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "request_count": len(recent_requests),
                    "limit": settings.RATE_LIMIT_PER_MINUTE
                }
            )
            
            raise RateLimitError(
                message="Too many requests. Please try again later.",
                retry_after=60
            )
        
        # Add current request
        recent_requests.append(current_time)
        self.requests[client_ip] = recent_requests
        
        return await call_next(request)
    
    def _clean_old_entries(self, current_time: float):
        """Remove entries older than the window."""
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if current_time - ts < self.window
            ]
            if not self.requests[ip]:
                del self.requests[ip]


def setup_cors(app):
    """
    Configure CORS middleware for the application.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=["X-Request-ID", "X-Total-Count", "X-Page", "X-Per-Page"],
    )
    
    logger.info(f"CORS configured with origins: {settings.CORS_ORIGINS}")


def setup_middleware(app):
    """
    Add all middleware to the application in the correct order.
    Middleware is applied in reverse order (last added, first executed).
    """
    
    # CORS (should be first in execution, so added last)
    setup_cors(app)
    
    # Error handling
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
    
    # Request logging (should be last in execution, so added first)
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("Middleware configured successfully")


__all__ = [
    "setup_middleware",
    "setup_cors",
    "RequestLoggingMiddleware",
    "ErrorHandlerMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
]
