"""Tests for Celery task entry points.

Tests that tasks delegate to use cases and dispatch next steps correctly.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import src.tasks as tasks_module
from src.application.use_cases.file_processing import WorkerPipelineStep
from src.domain.models import AlertRecord


NOW = datetime(2026, 4, 11, tzinfo=timezone.utc)


@dataclass(slots=True)
class FakePipelineUseCase:
    next_task_name: str
    file_id: str | None = None

    async def execute(self, file_id: str) -> WorkerPipelineStep:
        self.file_id = file_id
        return WorkerPipelineStep(task_name=self.next_task_name, file_id=file_id)


@dataclass(slots=True)
class FakeSendAlertUseCase:
    file_id: str | None = None

    async def execute(self, file_id: str) -> AlertRecord:
        self.file_id = file_id
        return AlertRecord(
            id=1,
            file_id=file_id,
            level="info",
            message="File processed successfully",
            created_at=NOW,
        )


def test_scan_task_delegates_to_use_case_and_dispatches_next_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that scan_file_for_threats calls use case and dispatches next step."""
    scan_use_case = FakePipelineUseCase(next_task_name="extract_file_metadata")
    sent_tasks: list[tuple[str, str]] = []

    # Patch dependencies
    monkeypatch.setattr(
        "src.tasks.get_scan_file_for_threats_use_case",
        lambda: scan_use_case,
    )
    monkeypatch.setattr(
        "src.tasks._ensure_db",
        lambda: None,
    )

    # Track sent tasks
    def fake_send_task(task_name: str, args: tuple) -> None:
        sent_tasks.append((task_name, args[0]))

    monkeypatch.setattr(tasks_module.celery_app, "send_task", fake_send_task)

    # Execute
    tasks_module.scan_file_for_threats("file-1")

    # Verify
    assert scan_use_case.file_id == "file-1"
    assert ("extract_file_metadata", "file-1") in sent_tasks


def test_extract_task_delegates_to_use_case_and_dispatches_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that extract_file_metadata calls use case and dispatches alert."""
    metadata_use_case = FakePipelineUseCase(next_task_name="send_file_alert")
    sent_tasks: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "src.tasks.get_extract_file_metadata_use_case",
        lambda: metadata_use_case,
    )
    monkeypatch.setattr(
        "src.tasks._ensure_db",
        lambda: None,
    )

    def fake_send_task(task_name: str, args: tuple) -> None:
        sent_tasks.append((task_name, args[0]))

    monkeypatch.setattr(tasks_module.celery_app, "send_task", fake_send_task)

    tasks_module.extract_file_metadata("file-1")

    assert metadata_use_case.file_id == "file-1"
    assert ("send_file_alert", "file-1") in sent_tasks


def test_alert_task_is_terminal_and_dispatches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that send_file_alert is terminal and doesn't dispatch."""
    alert_use_case = FakeSendAlertUseCase()
    sent_tasks: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "src.tasks.get_send_file_alert_use_case",
        lambda: alert_use_case,
    )
    monkeypatch.setattr(
        "src.tasks._ensure_db",
        lambda: None,
    )

    def fake_send_task(task_name: str, args: tuple) -> None:
        sent_tasks.append((task_name, args[0]))

    monkeypatch.setattr(tasks_module.celery_app, "send_task", fake_send_task)

    tasks_module.send_file_alert("file-1")

    assert alert_use_case.file_id == "file-1"
    assert len(sent_tasks) == 0  # Terminal task
