from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class FileRecord:
    id: str
    title: str
    original_name: str
    stored_name: str
    mime_type: str
    size: int
    processing_status: str
    scan_status: str | None
    scan_details: str | None
    metadata_json: dict[str, object] | None
    requires_attention: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AlertRecord:
    id: int
    file_id: str
    level: str
    message: str
    created_at: datetime
