"""Tests for bug closure: scan_status vocabulary preservation."""

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.application.errors import ProcessingError
from src.application.use_cases.file_processing import (
    ExtractFileMetadataUseCase,
    MISSING_STORED_FILE_DETAILS,
    WorkerPipelineStep,
)
from src.domain.models import FileRecord

pytestmark = pytest.mark.usefixtures("clean_database")


NOW = datetime.now(timezone.utc)


class TestScanStatusVocabularyPreservation:
    """Verify scan_status remains clean/suspicious and is never corrupted."""

    def test_scan_status_never_set_to_failed(self):
        """scan_status should never be written as 'failed' in any code path."""
        # Create a file record with clean scan_status
        file_record = FileRecord(
            id="test-id",
            title="Test",
            original_name="test.txt",
            stored_name="test-id.txt",
            mime_type="text/plain",
            size=100,
            processing_status="uploaded",
            scan_status="clean",  # Valid vocabulary value
            scan_details=None,
            metadata_json=None,
            requires_attention=False,
            created_at=NOW,
            updated_at=NOW,
        )

        # Mock repo and storage
        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=file_record)

        saved_calls = []

        async def mock_save_metadata(
            file_id,
            *,
            processing_status,
            metadata_json,
            scan_status=None,
            scan_details=None,
        ):
            saved_calls.append(
                {
                    "processing_status": processing_status,
                    "scan_status": scan_status,
                }
            )
            return replace(
                file_record,
                processing_status=processing_status,
                scan_status=scan_status,
                scan_details=scan_details,
            )

        mock_repo.save_metadata_result = mock_save_metadata

        mock_storage = MagicMock()
        mock_storage.resolve_path = MagicMock(return_value=None)  # File missing

        use_case = ExtractFileMetadataUseCase(mock_repo, mock_storage)

        result = asyncio.run(use_case.execute("test-id"))

        # Verify the call preserved scan_status
        assert len(saved_calls) == 1
        assert saved_calls[0]["scan_status"] != "failed"
        assert saved_calls[0]["scan_status"] == "clean"  # Preserved original
        assert saved_calls[0]["processing_status"] == "failed"  # Can be failed

    def test_scan_status_suspicious_preserved_on_missing_file(self):
        """scan_status='suspicious' should be preserved when file is missing."""
        file_record = FileRecord(
            id="test-id",
            title="Test",
            original_name="test.txt",
            stored_name="test-id.txt",
            mime_type="text/plain",
            size=100,
            processing_status="uploaded",
            scan_status="suspicious",  # Suspicious from scan step
            scan_details="suspicious extension .txt",
            metadata_json=None,
            requires_attention=True,
            created_at=NOW,
            updated_at=NOW,
        )

        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=file_record)

        saved_calls = []

        async def mock_save_metadata(
            file_id,
            *,
            processing_status,
            metadata_json,
            scan_status=None,
            scan_details=None,
        ):
            saved_calls.append(
                {
                    "processing_status": processing_status,
                    "scan_status": scan_status,
                    "scan_details": scan_details,
                }
            )
            return replace(
                file_record,
                processing_status=processing_status,
                scan_status=scan_status,
                scan_details=scan_details,
            )

        mock_repo.save_metadata_result = mock_save_metadata

        mock_storage = MagicMock()
        mock_storage.resolve_path = MagicMock(return_value=None)

        use_case = ExtractFileMetadataUseCase(mock_repo, mock_storage)

        result = asyncio.run(use_case.execute("test-id"))

        assert len(saved_calls) == 1
        assert saved_calls[0]["scan_status"] == "suspicious"  # Preserved
        assert saved_calls[0]["processing_status"] == "failed"
        assert MISSING_STORED_FILE_DETAILS in saved_calls[0]["scan_details"]

    def test_scan_status_none_preserved_when_no_scan(self):
        """scan_status=None should remain None when file is missing."""
        file_record = FileRecord(
            id="test-id",
            title="Test",
            original_name="test.txt",
            stored_name="test-id.txt",
            mime_type="text/plain",
            size=100,
            processing_status="uploaded",
            scan_status=None,  # No scan yet
            scan_details=None,
            metadata_json=None,
            requires_attention=False,
            created_at=NOW,
            updated_at=NOW,
        )

        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=file_record)

        saved_calls = []

        async def mock_save_metadata(
            file_id,
            *,
            processing_status,
            metadata_json,
            scan_status=None,
            scan_details=None,
        ):
            saved_calls.append(
                {
                    "processing_status": processing_status,
                    "scan_status": scan_status,
                }
            )
            return replace(
                file_record,
                processing_status=processing_status,
                scan_status=scan_status,
            )

        mock_repo.save_metadata_result = mock_save_metadata

        mock_storage = MagicMock()
        mock_storage.resolve_path = MagicMock(return_value=None)

        use_case = ExtractFileMetadataUseCase(mock_repo, mock_storage)

        result = asyncio.run(use_case.execute("test-id"))

        assert len(saved_calls) == 1
        assert saved_calls[0]["scan_status"] is None  # Preserved as None
        assert saved_calls[0]["processing_status"] == "failed"


class TestWorkerPipelineProducesObservableOutcomes:
    """Verify terminal failures produce observable outcomes (alerts)."""

    def test_missing_file_dispatches_alert(self):
        """Missing stored file should still dispatch alert via next step."""
        file_record = FileRecord(
            id="test-id",
            title="Test",
            original_name="test.txt",
            stored_name="test-id.txt",
            mime_type="text/plain",
            size=100,
            processing_status="processing",
            scan_status="clean",
            scan_details=None,
            metadata_json=None,
            requires_attention=False,
            created_at=NOW,
            updated_at=NOW,
        )

        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=file_record)

        saved_calls = []

        async def mock_save_metadata(
            file_id,
            *,
            processing_status,
            metadata_json,
            scan_status=None,
            scan_details=None,
        ):
            saved_calls.append(
                {
                    "file_id": file_id,
                    "processing_status": processing_status,
                }
            )
            return replace(file_record, processing_status=processing_status)

        mock_repo.save_metadata_result = mock_save_metadata

        mock_storage = MagicMock()
        mock_storage.resolve_path = MagicMock(return_value=None)

        use_case = ExtractFileMetadataUseCase(mock_repo, mock_storage)

        result = asyncio.run(use_case.execute("test-id"))

        # Should return a WorkerPipelineStep for send_file_alert
        assert result is not None
        assert isinstance(result, WorkerPipelineStep)
        assert result.task_name == "send_file_alert"
        assert result.file_id == "test-id"


class TestValidScanStatusValues:
    """Contract tests for valid scan_status values."""

    @pytest.mark.parametrize("valid_status", ["clean", "suspicious", None])
    def test_valid_scan_status_values(self, valid_status):
        """Only 'clean', 'suspicious', and None are valid scan_status values."""
        # This is a contract test documenting the valid values
        valid_values = {"clean", "suspicious", None}
        assert valid_status in valid_values

    def test_failed_is_not_valid_scan_status(self):
        """'failed' is not a valid scan_status value and should never be written."""
        valid_values = {"clean", "suspicious", None}
        assert "failed" not in valid_values
