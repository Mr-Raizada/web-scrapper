from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AppException(Exception):
    """Base application exception"""
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)

class ValidationException(AppException):
    """Validation error exception"""
    def __init__(self, detail: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail, error_code)

class AuthenticationException(AppException):
    """Authentication error exception"""
    def __init__(self, detail: str = "Authentication failed", error_code: str = "AUTH_ERROR"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, error_code)

class AuthorizationException(AppException):
    """Authorization error exception"""
    def __init__(self, detail: str = "Insufficient permissions", error_code: str = "FORBIDDEN"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, error_code)

class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, error_code)

class RateLimitException(AppException):
    """Rate limiting exception"""
    def __init__(self, detail: str = "Rate limit exceeded", error_code: str = "RATE_LIMIT"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, detail, error_code)

class ScrapingException(AppException):
    """Scraping operation exception"""
    def __init__(self, detail: str = "Scraping operation failed", error_code: str = "SCRAPING_ERROR"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, error_code)

class DatabaseException(AppException):
    """Database operation exception"""
    def __init__(self, detail: str = "Database operation failed", error_code: str = "DB_ERROR"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, error_code)

class ExternalServiceException(AppException):
    """External service exception"""
    def __init__(self, detail: str = "External service error", error_code: str = "EXTERNAL_ERROR"):
        super().__init__(status.HTTP_502_BAD_GATEWAY, detail, error_code)

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions"""
    logger.error(f"Application exception: {exc.detail}", extra={
        "status_code": exc.status_code,
        "error_code": exc.error_code,
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "timestamp": str(request.state.timestamp) if hasattr(request.state, 'timestamp') else None
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}", extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None
    })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
                "timestamp": str(request.state.timestamp) if hasattr(request.state, 'timestamp') else None
            }
        }
    )

async def python_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected Python exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True, extra={
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": str(request.state.timestamp) if hasattr(request.state, 'timestamp') else None
            }
        }
    )

def log_request_info(request: Request) -> Dict[str, Any]:
    """Log request information for debugging"""
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "content_length": request.headers.get("content-length"),
    } 