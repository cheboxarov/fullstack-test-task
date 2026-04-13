from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field


T = TypeVar("T")

# Type alias for field-level validation errors
ApiErrorFieldMap = dict[str, list[str]]


class ApiErrorPayload(BaseModel):
    """Standardized API error payload per Phase 1 error model.

    Provides consistent error structure across all API endpoints
    with support for field-level validation errors and request tracking.
    """

    code: str = Field(description="Stable error code for client handling")
    message: str = Field(description="User-facing error message in Russian")
    details: Optional[dict] = Field(
        default=None, description="Additional error context"
    )
    fields: Optional[ApiErrorFieldMap] = Field(
        default=None,
        description="Field-level validation errors (field -> list of messages)",
    )
    retryable: bool = Field(
        default=False, description="Whether client can retry the request"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request ID for error correlation"
    )


class ApiErrorResponse(BaseModel):
    """Wrapper model for API error responses.

    All error responses are wrapped in an 'error' key for consistent parsing.
    """

    error: ApiErrorPayload


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model per D-01.

    Provides consistent pagination contract across all list endpoints.
    """

    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        """Calculate total pages (ceiling of total/page_size)."""
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class FileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_name: str
    mime_type: str
    size: int
    processing_status: str
    scan_status: Optional[str]
    scan_details: Optional[str]
    metadata_json: Optional[dict]
    requires_attention: bool
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255, description="File title")


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: str
    level: str
    message: str
    created_at: datetime
