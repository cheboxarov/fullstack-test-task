from src.application.ports import AlertRepository
from src.domain.models import AlertRecord


class ListAlertsUseCase:
    def __init__(self, alert_repository: AlertRepository) -> None:
        self.alert_repository = alert_repository

    async def execute(self) -> list[AlertRecord]:
        return await self.alert_repository.list_alerts()


class ListAlertsPaginatedUseCase:
    """Paginated alert listing per D-01, D-02, D-03."""

    def __init__(self, alert_repository: AlertRepository) -> None:
        self.alert_repository = alert_repository

    async def execute(self, page: int, page_size: int) -> tuple[list[AlertRecord], int]:
        """Execute paginated alert query.

        Args:
            page: Page number (1-based, clamped to >= 1)
            page_size: Items per page (clamped 1-100 per D-02)

        Returns:
            Tuple of (alert_records, total_count)
        """
        # Validate and clamp parameters per D-02, T-05-01-01, T-05-01-04
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:  # Per D-02 max, T-05-01-02 DoS prevention
            page_size = 100

        offset = (page - 1) * page_size
        items, total = await self.alert_repository.list_alerts_paginated(
            offset, page_size
        )

        return items, total
