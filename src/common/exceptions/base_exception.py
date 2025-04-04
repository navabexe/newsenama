# File: common/exceptions/base_exception.py

from fastapi import HTTPException, status


class TooManyRequestsException(HTTPException):
    def __init__(self, detail: str = "Too many requests. Please try again later."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Unauthorized access."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "You do not have permission to access this resource."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequestException(HTTPException):
    def __init__(self, detail: str = "Invalid request parameters."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class ConflictException(HTTPException):
    def __init__(self, detail: str = "Resource conflict detected."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class InternalServerErrorException(HTTPException):
    def __init__(self, detail: str = "Internal server error occurred."):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class ServiceUnavailableException(HTTPException):
    def __init__(self, detail: str = "Service temporarily unavailable. Please try again later."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


