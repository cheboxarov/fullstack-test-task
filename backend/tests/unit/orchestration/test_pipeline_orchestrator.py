"""Unit tests for PipelineOrchestrator.

Tests all state transitions in the worker pipeline per D-02.
Uses mocks for use cases - testing orchestrator logic in isolation.
"""

import pytest
from unittest.mock import MagicMock

from src.application.orchestration.pipeline_orchestrator import PipelineOrchestrator
from src.application.use_cases.file_processing import WorkerPipelineStep
from src.application.errors import ProcessingError


@pytest.fixture
def orchestrator():
    """Create a PipelineOrchestrator instance for testing."""
    return PipelineOrchestrator()


def test_scan_success_triggers_metadata(orchestrator):
    """Test that successful scan triggers metadata extraction step."""
    current_step = WorkerPipelineStep(task_name="scan_file_for_threats", file_id="123")
    result = MagicMock()  # Successful result

    next_step = orchestrator.determine_next_step(current_step, result, None)

    assert next_step is not None
    assert next_step.task_name == "extract_file_metadata"
    assert next_step.file_id == "123"


def test_metadata_success_triggers_alert(orchestrator):
    """Test that successful metadata extraction triggers alert step."""
    current_step = WorkerPipelineStep(task_name="extract_file_metadata", file_id="456")
    result = MagicMock()  # Successful result

    next_step = orchestrator.determine_next_step(current_step, result, None)

    assert next_step is not None
    assert next_step.task_name == "send_file_alert"
    assert next_step.file_id == "456"


def test_alert_completion_terminates_pipeline(orchestrator):
    """Test that alert completion returns None (pipeline termination)."""
    current_step = WorkerPipelineStep(task_name="send_file_alert", file_id="789")
    result = MagicMock()  # Alert result

    next_step = orchestrator.determine_next_step(current_step, result, None)

    assert next_step is None


def test_scan_processing_error_triggers_alert(orchestrator):
    """Test that ProcessingError during scan triggers alert (terminal handling)."""
    current_step = WorkerPipelineStep(task_name="scan_file_for_threats", file_id="101")
    error = ProcessingError("Scan failed")

    next_step = orchestrator.determine_next_step(current_step, None, error)

    assert next_step is not None
    assert next_step.task_name == "send_file_alert"
    assert next_step.file_id == "101"


def test_metadata_processing_error_triggers_alert(orchestrator):
    """Test that ProcessingError during metadata extraction triggers alert."""
    current_step = WorkerPipelineStep(task_name="extract_file_metadata", file_id="202")
    error = ProcessingError("Metadata extraction failed")

    next_step = orchestrator.determine_next_step(current_step, None, error)

    assert next_step is not None
    assert next_step.task_name == "send_file_alert"
    assert next_step.file_id == "202"


def test_none_result_from_scan_triggers_alert(orchestrator):
    """Test that None result from scan triggers alert step."""
    current_step = WorkerPipelineStep(task_name="scan_file_for_threats", file_id="303")

    next_step = orchestrator.determine_next_step(current_step, None, None)

    assert next_step is not None
    assert next_step.task_name == "send_file_alert"
    assert next_step.file_id == "303"


def test_none_result_from_metadata_triggers_alert(orchestrator):
    """Test that None result from metadata extraction triggers alert step."""
    current_step = WorkerPipelineStep(task_name="extract_file_metadata", file_id="404")

    next_step = orchestrator.determine_next_step(current_step, None, None)

    assert next_step is not None
    assert next_step.task_name == "send_file_alert"
    assert next_step.file_id == "404"


def test_error_with_no_file_id_returns_none(orchestrator):
    """Test that error with no file_id context returns None."""
    current_step = None  # No step context
    error = ProcessingError("Unknown error")

    next_step = orchestrator.determine_next_step(current_step, None, error)

    assert next_step is None


def test_unknown_step_returns_none(orchestrator):
    """Test that unknown step name terminates pipeline."""
    current_step = WorkerPipelineStep(task_name="unknown_step", file_id="505")
    result = MagicMock()

    next_step = orchestrator.determine_next_step(current_step, result, None)

    assert next_step is None


def test_create_metadata_step_helper(orchestrator):
    """Test internal helper for creating metadata step."""
    step = orchestrator._create_metadata_step("test-file-123")

    assert step.task_name == "extract_file_metadata"
    assert step.file_id == "test-file-123"


def test_create_alert_step_helper(orchestrator):
    """Test internal helper for creating alert step."""
    step = orchestrator._create_alert_step("test-file-456")

    assert step.task_name == "send_file_alert"
    assert step.file_id == "test-file-456"


def test_extract_file_id_from_step(orchestrator):
    """Test internal helper for extracting file_id from step."""
    step = WorkerPipelineStep(task_name="scan_file_for_threats", file_id="extract-test")

    file_id = orchestrator._extract_file_id(step, None)

    assert file_id == "extract-test"
