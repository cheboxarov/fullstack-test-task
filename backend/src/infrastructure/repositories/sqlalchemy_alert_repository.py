"""SQLAlchemy alert repository with cascade delete support."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.models import AlertRecord
from src.infrastructure.mappers.orm_domain import alert_to_domain
from src.infrastructure.models import Alert


class SqlAlchemyAlertRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def list_alerts(self) -> list[AlertRecord]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Alert).order_by(Alert.created_at.desc())
            )
            return [alert_to_domain(alert_row) for alert_row in result.scalars().all()]

    async def list_alerts_paginated(
        self, offset: int, limit: int
    ) -> tuple[list[AlertRecord], int]:
        """Return paginated alerts with total count per D-04.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (items, total_count)
        """
        async with self.session_maker() as session:
            # Get total count
            count_result = await session.execute(
                select(func.count()).select_from(Alert)
            )
            total = count_result.scalar() or 0

            # Get paginated items ordered by created_at desc (per D-02)
            result = await session.execute(
                select(Alert)
                .order_by(Alert.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            items = [alert_to_domain(alert_row) for alert_row in result.scalars().all()]
            return items, total

    async def create_alert(
        self,
        *,
        file_id: str,
        level: str,
        message: str,
    ) -> AlertRecord:
        alert = Alert(file_id=file_id, level=level, message=message)

        async with self.session_maker() as session:
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert_to_domain(alert)

    async def delete_alerts_for_file(
        self, file_id: str, session: AsyncSession | None = None
    ) -> int:
        """Delete all alerts for a given file_id.

        Args:
            file_id: The file ID whose alerts should be deleted
            session: Optional session to use (for transaction sharing)

        Returns:
            Number of alerts deleted
        """
        if session is not None:
            # Use provided session (same transaction)
            result = await session.execute(
                delete(Alert).where(Alert.file_id == file_id)
            )
            return result.rowcount or 0
        else:
            # Create own session
            async with self.session_maker() as session:
                result = await session.execute(
                    delete(Alert).where(Alert.file_id == file_id)
                )
                await session.commit()
                return result.rowcount or 0
