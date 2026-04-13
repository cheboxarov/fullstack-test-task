"""PipelineOrchestrator - centralized routing logic for worker pipeline.

Implements pure routing logic per D-02: determines the next step in the
worker pipeline based on current step, result, and any error.

Pipeline flow: scan → metadata → alert
"""

from src.application.use_cases.file_processing import WorkerPipelineStep


class PipelineOrchestrator:
    """Orchestrates worker pipeline transitions.

    Pure application layer component with no external dependencies.
    Decides next step based on current state and use case results.
    """

    def __init__(self) -> None:
        """Initialize orchestrator with transition rules."""
        pass

    def determine_next_step(
        self,
        current_step: "WorkerPipelineStep | None",
        result: object | None,
        error: Exception | None,
    ) -> "WorkerPipelineStep | None":
        """Determine the next pipeline step based on current state.

        Args:
            current_step: The step that just completed (None for initial)
            result: The result returned by the use case execution
            error: Any exception raised during execution

        Returns:
            WorkerPipelineStep for next task, or None to terminate pipeline
        """
        # Handle terminal errors - always route to alert
        if error is not None:
            # Get file_id from current step or result
            file_id = self._extract_file_id(current_step, result)
            if file_id:
                return self._create_alert_step(file_id)
            return None

        # Handle normal flow transitions based on current step
        if current_step is None:
            # Initial state - start with scan
            return None  # Scan should be triggered externally

        # Transition: scan success → metadata
        if current_step.task_name == "scan_file_for_threats":
            if result is not None:
                # Success - schedule metadata extraction
                return self._create_metadata_step(current_step.file_id)
            return self._create_alert_step(current_step.file_id)

        # Transition: metadata success → alert
        if current_step.task_name == "extract_file_metadata":
            if result is not None:
                # Success - schedule alert
                return self._create_alert_step(current_step.file_id)
            return self._create_alert_step(current_step.file_id)

        # Alert is terminal - no next step
        if current_step.task_name == "send_file_alert":
            return None

        # Unknown step - terminate pipeline
        return None

    def _extract_file_id(
        self,
        current_step: "WorkerPipelineStep | None",
        result: object | None,
    ) -> str | None:
        """Extract file_id from current step or result."""
        if current_step is not None:
            return current_step.file_id
        return None

    def _create_metadata_step(self, file_id: str) -> WorkerPipelineStep:
        """Create a metadata extraction step."""
        return WorkerPipelineStep(
            task_name="extract_file_metadata",
            file_id=file_id,
        )

    def _create_alert_step(self, file_id: str) -> WorkerPipelineStep:
        """Create an alert sending step."""
        return WorkerPipelineStep(
            task_name="send_file_alert",
            file_id=file_id,
        )
