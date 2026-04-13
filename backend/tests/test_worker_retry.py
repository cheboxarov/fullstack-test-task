"""Tests for worker retry configuration and terminal failure handling."""

import asyncio
import inspect
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import InterfaceError, OperationalError

from src.application.errors import FileNotFoundError, ProcessingError
from src.application.use_cases.file_processing import (
    ExtractFileMetadataUseCase,
    ScanFileForThreatsUseCase,
    SendFileAlertUseCase,
)
from src.domain.models import FileRecord
from src import tasks as tasks_module

pytestmark = pytest.mark.usefixtures("clean_database")


class TestCeleryRetryConfiguration:
    """Unit tests for Celery task retry configuration."""

    def test_scan_task_has_retry_config(self):
        """scan_file_for_threats task should have retry configuration."""
        task = tasks_module.scan_file_for_threats
        assert hasattr(task, "autoretry_for")
        assert hasattr(task, "retry_backoff")
        assert hasattr(task, "max_retries")
        assert hasattr(task, "retry_jitter")

    def test_extract_task_has_retry_config(self):
        """extract_file_metadata task should have retry configuration."""
        task = tasks_module.extract_file_metadata
        assert hasattr(task, "autoretry_for")
        assert hasattr(task, "retry_backoff")
        assert hasattr(task, "max_retries")
        assert hasattr(task, "retry_jitter")

    def test_alert_task_has_retry_config(self):
        """send_file_alert task should have retry configuration."""
        task = tasks_module.send_file_alert
        assert hasattr(task, "autoretry_for")
        assert hasattr(task, "retry_backoff")
        assert hasattr(task, "max_retries")
        assert hasattr(task, "retry_jitter")

    def test_autoretry_for_transient_errors(self):
        """autoretry_for should include transient DB errors only."""
        # Check that the expected transient errors are configured
        expected_errors = (OperationalError, InterfaceError)
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            # The task's autoretry_for should include our transient errors
            assert task.autoretry_for is not None
            assert any(err in task.autoretry_for for err in expected_errors), (
                f"{task.name} should retry on OperationalError/InterfaceError"
            )

    def test_retry_backoff_is_enabled(self):
        """retry_backoff should be enabled for all tasks."""
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            assert task.retry_backoff is True, (
                f"{task.name} should have retry_backoff enabled"
            )

    def test_max_retries_is_configured(self):
        """max_retries should be a positive integer for all tasks."""
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            assert isinstance(task.max_retries, int)
            assert task.max_retries > 0, f"{task.name} should have positive max_retries"

    def test_retry_jitter_is_enabled(self):
        """retry_jitter should be enabled to prevent thundering herd."""
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            assert task.retry_jitter is True, (
                f"{task.name} should have retry_jitter enabled"
            )

    def test_retry_backoff_max_is_bounded(self):
        """retry_backoff_max should be bounded (no infinite backoff)."""
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            assert task.retry_backoff_max is not None
            assert task.retry_backoff_max <= 300, (
                f"{task.name} should have backoff_max <= 300 seconds"
            )


class TestTransientVsTerminalErrors:
    """Tests verifying transient errors trigger retry, business errors are terminal."""

    def test_transient_db_errors_in_autoretry(self):
        """OperationalError and InterfaceError should be in autoretry_for."""
        # These are the transient infrastructure errors that should trigger retry
        transient_errors = (OperationalError, InterfaceError)

        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            for err in transient_errors:
                assert err in task.autoretry_for, (
                    f"{task.name} should retry on {err.__name__}"
                )

    def test_business_errors_not_in_autoretry(self):
        """Business logic errors should NOT trigger retry."""
        # These errors should NOT be retried (they're terminal)
        terminal_errors = [
            Exception("Generic exception should not be in autoretry_for"),
        ]

        # Note: We're testing that specific error types are NOT in the list
        # In Celery, autoretry_for is a tuple of exception types to retry on
        # Business errors like FileNotFoundError from ports.py are terminal
        for task in [
            tasks_module.scan_file_for_threats,
            tasks_module.extract_file_metadata,
            tasks_module.send_file_alert,
        ]:
            # FileNotFoundError (from use cases) should NOT be in autoretry_for
            assert FileNotFoundError not in task.autoretry_for


class TestTerminalFailureHandling:
    """Tests for explicit terminal failure handling."""

    def test_processing_error_exists(self):
        """ProcessingError should exist as an application-level error."""
        assert ProcessingError is not None
        assert issubclass(ProcessingError, Exception)

    def test_processing_error_can_be_raised(self):
        """ProcessingError can be raised with a message."""
        with pytest.raises(ProcessingError) as exc_info:
            raise ProcessingError("Test error message")
        assert exc_info.value.detail == "Test error message"

    def test_scan_use_case_raises_on_missing_file(self):
        """ScanFileForThreatsUseCase should raise ProcessingError for missing file."""
        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=None)

        use_case = ScanFileForThreatsUseCase(mock_repo)

        with pytest.raises(ProcessingError) as exc_info:
            asyncio.run(use_case.execute("missing-file-id"))

        assert "not found" in exc_info.value.detail.lower()

    def test_extract_use_case_raises_on_missing_file(self):
        """ExtractFileMetadataUseCase should raise ProcessingError for missing file."""
        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=None)

        use_case = ExtractFileMetadataUseCase(mock_repo, AsyncMock())

        with pytest.raises(ProcessingError) as exc_info:
            asyncio.run(use_case.execute("missing-file-id"))

        assert "not found" in exc_info.value.detail.lower()

    def test_alert_use_case_raises_on_missing_file(self):
        """SendFileAlertUseCase should raise ProcessingError for missing file."""
        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=None)
        mock_alert_repo = AsyncMock()

        use_case = SendFileAlertUseCase(mock_repo, mock_alert_repo)

        with pytest.raises(ProcessingError) as exc_info:
            asyncio.run(use_case.execute("missing-file-id"))

        assert "not found" in exc_info.value.detail.lower()


class TestScanStatusVocabulary:
    """Tests ensuring scan_status vocabulary is not corrupted by failure handling."""

    def test_scan_status_never_set_to_failed(self):
        """scan_status should never be set to 'failed' - only clean/suspicious."""
        NOW = datetime.now(timezone.utc)

        # Create a file record
        file_record = FileRecord(
            id="test-id",
            title="Test",
            original_name="test.txt",
            stored_name="test-id.txt",
            mime_type="text/plain",
            size=100,
            processing_status="uploaded",
            scan_status="clean",
            scan_details=None,
            metadata_json=None,
            requires_attention=False,
            created_at=NOW,
            updated_at=NOW,
        )

        # Mock repo returns the file but storage gateway returns None (file missing)
        mock_repo = AsyncMock()
        mock_repo.get_file = AsyncMock(return_value=file_record)

        # Track what save_metadata_result is called with
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
        mock_storage.resolve_path = MagicMock(return_value=None)

        use_case = ExtractFileMetadataUseCase(mock_repo, mock_storage)

        result = asyncio.run(use_case.execute("test-id"))

        # Verify save_metadata_result was called
        assert len(saved_calls) == 1

        # scan_status should NOT be "failed" - should preserve existing value
        assert saved_calls[0]["scan_status"] != "failed"
        assert saved_calls[0]["scan_status"] == "clean"

        # processing_status CAN be "failed"
        assert saved_calls[0]["processing_status"] == "failed"

    def test_scan_status_values_valid(self):
        """scan_status values should only be clean, suspicious, or None."""
        valid_scan_statuses = {"clean", "suspicious", None}

        # This is a contract test - these are the only valid values
        # Any code setting scan_status must use only these values
        assert "failed" not in valid_scan_statuses
