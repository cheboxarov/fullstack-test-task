from fastapi import APIRouter, Depends, Query

from src.application.use_cases.alert_queries import (
    ListAlertsPaginatedUseCase,
    ListAlertsUseCase,
)
from src.bootstrap.container import (
    get_list_alerts_paginated_use_case,
    get_list_alerts_use_case,
)
from src.presentation.mappers.dto import domain_alert_to_dto
from src.presentation.schemas import AlertItem, PaginatedResponse


alerts_router = APIRouter()


@alerts_router.get("/alerts", response_model=PaginatedResponse[AlertItem])
async def list_alerts_view(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    use_case: ListAlertsPaginatedUseCase = Depends(get_list_alerts_paginated_use_case),
):
    """List alerts with pagination per D-01, D-03.

    Query parameters:
    - page: Page number (default: 1, minimum: 1)
    - page_size: Items per page (default: 10, min: 1, max: 100 per D-02)
    """
    items, total = await use_case.execute(page=page, page_size=page_size)
    return PaginatedResponse(
        items=[domain_alert_to_dto(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
