from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    status_code: int = Field(alias="statusCode")
    message: str
    data: Optional[T] = None

    model_config = {"populate_by_name": True}


def success(data: Any = None, message: str = "Success", status_code: int = 200) -> dict:
    return {"statusCode": status_code, "message": message, "data": data}


def error(message: str, status_code: int = 400, data: Any = None) -> dict:
    return {"statusCode": status_code, "message": message, "data": data}
