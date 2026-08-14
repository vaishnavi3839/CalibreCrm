from typing import Optional

from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, message: str, status_code: int = 400, details: Optional[dict] = None):
        super().__init__(status_code=status_code, detail={"message": message, "details": details or {}})


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    def __init__(self, message: str = "Not found"):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class ValidationAppError(AppException):
    def __init__(self, message: str = "Validation error", details: Optional[dict] = None):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)
