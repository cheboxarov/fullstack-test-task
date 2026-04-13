from src.domain.models import AlertRecord, FileRecord
from src.presentation.schemas import AlertItem, FileItem


def domain_file_to_dto(file_record: FileRecord) -> FileItem:
    return FileItem(
        id=file_record.id,
        title=file_record.title,
        original_name=file_record.original_name,
        mime_type=file_record.mime_type,
        size=file_record.size,
        processing_status=file_record.processing_status,
        scan_status=file_record.scan_status,
        scan_details=file_record.scan_details,
        metadata_json=dict(file_record.metadata_json)
        if file_record.metadata_json
        else None,
        requires_attention=file_record.requires_attention,
        created_at=file_record.created_at,
        updated_at=file_record.updated_at,
    )


def domain_alert_to_dto(alert_record: AlertRecord) -> AlertItem:
    return AlertItem(
        id=alert_record.id,
        file_id=alert_record.file_id,
        level=alert_record.level,
        message=alert_record.message,
        created_at=alert_record.created_at,
    )
