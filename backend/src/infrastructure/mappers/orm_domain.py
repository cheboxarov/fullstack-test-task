from src.domain.models import AlertRecord, FileRecord
from src.infrastructure.models import Alert, StoredFile


def stored_file_to_domain(stored_file: StoredFile) -> FileRecord:
    return FileRecord(
        id=stored_file.id,
        title=stored_file.title,
        original_name=stored_file.original_name,
        stored_name=stored_file.stored_name,
        mime_type=stored_file.mime_type,
        size=stored_file.size,
        processing_status=stored_file.processing_status,
        scan_status=stored_file.scan_status,
        scan_details=stored_file.scan_details,
        metadata_json=dict(stored_file.metadata_json)
        if stored_file.metadata_json
        else None,
        requires_attention=stored_file.requires_attention,
        created_at=stored_file.created_at,
        updated_at=stored_file.updated_at,
    )


def alert_to_domain(alert: Alert) -> AlertRecord:
    return AlertRecord(
        id=alert.id,
        file_id=alert.file_id,
        level=alert.level,
        message=alert.message,
        created_at=alert.created_at,
    )
