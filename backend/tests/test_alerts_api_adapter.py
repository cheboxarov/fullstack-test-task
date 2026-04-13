from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.domain.models import AlertRecord
from src.presentation.schemas import AlertItem, PaginatedResponse
from src.presentation.api.alerts import list_alerts_view
from src.presentation.mappers.dto import domain_alert_to_dto


NOW = datetime(2026, 4, 11, tzinfo=timezone.utc)


@dataclass(slots=True)
class FakeListAlertsPaginatedUseCase:
    alert_records: list[AlertRecord]
    called: bool = False

    async def execute(self, page: int, page_size: int) -> tuple[list[AlertRecord], int]:
        self.called = True
        return self.alert_records, len(self.alert_records)


@pytest.mark.asyncio
async def test_list_alerts_view_maps_domain_records_via_use_case() -> None:
    use_case = FakeListAlertsPaginatedUseCase(
        alert_records=[
            AlertRecord(
                id=2,
                file_id="file-2",
                level="warning",
                message="second",
                created_at=NOW,
            ),
            AlertRecord(
                id=1,
                file_id="file-1",
                level="info",
                message="first",
                created_at=NOW,
            ),
        ]
    )

    response = await list_alerts_view(page=1, page_size=10, use_case=use_case)

    assert use_case.called is True
    assert response.total == 2
    assert len(response.items) == 2
