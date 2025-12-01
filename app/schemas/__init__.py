# Pydantic schemas package
from pydantic import BaseModel

from app.schemas.base import (
    BaseRequestSchema,
    BaseResponseSchema,
    BaseSchema,
    PaginationRequestSchema,
    PaginationResponseSchema,
)


class HealthResponse(BaseModel):
    status: str


__all__ = [
    "BaseSchema",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "PaginationRequestSchema",
    "PaginationResponseSchema",
    "HealthResponse",
]
