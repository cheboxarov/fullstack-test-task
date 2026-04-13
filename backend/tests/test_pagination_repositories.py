"""Tests for paginated repository methods per D-04."""

import inspect

import pytest
from src.bootstrap.container import get_engine
from src.bootstrap.database import create_session_maker
from src.infrastructure.repositories.sqlalchemy_file_repository import (
    SqlAlchemyFileRepository,
)
from src.infrastructure.repositories.sqlalchemy_alert_repository import (
    SqlAlchemyAlertRepository,
)


class TestFileRepositoryPagination:
    """Test suite for SqlAlchemyFileRepository pagination."""

    @pytest.mark.asyncio
    async def test_list_files_paginated_method_exists(self, clean_database):
        """Test: list_files_paginated method exists and has correct signature."""
        # Arrange - create repository with session maker
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyFileRepository(session_maker)

        # Act & Assert - method should exist and be callable
        assert hasattr(repo, "list_files_paginated")
        sig = inspect.signature(repo.list_files_paginated)
        params = list(sig.parameters.keys())
        assert "offset" in params
        assert "limit" in params

    @pytest.mark.asyncio
    async def test_list_files_paginated_returns_tuple(self, clean_database):
        """Test 1: list_files_paginated(0, 10) returns (items, total) tuple."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyFileRepository(session_maker)

        # Act
        items, total = await repo.list_files_paginated(offset=0, limit=10)

        # Assert
        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total >= 0
        assert len(items) <= 10

    @pytest.mark.asyncio
    async def test_list_files_paginated_offset_works(self, clean_database):
        """Test 2: list_files_paginated(10, 10) returns next page."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyFileRepository(session_maker)

        # Act
        items, total = await repo.list_files_paginated(offset=10, limit=10)

        # Assert
        assert isinstance(items, list)
        assert len(items) <= 10
        assert isinstance(total, int)

    @pytest.mark.asyncio
    async def test_list_files_paginated_total_consistent(self, clean_database):
        """Test 3: Total count is consistent regardless of limit."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyFileRepository(session_maker)

        # Act - get total with different limits
        _, total_small = await repo.list_files_paginated(offset=0, limit=5)
        _, total_large = await repo.list_files_paginated(offset=0, limit=100)

        # Assert - total should be the same
        assert total_small == total_large


class TestAlertRepositoryPagination:
    """Test suite for SqlAlchemyAlertRepository pagination."""

    @pytest.mark.asyncio
    async def test_list_alerts_paginated_method_exists(self, clean_database):
        """Test: list_alerts_paginated method exists and has correct signature."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyAlertRepository(session_maker)

        # Assert
        assert hasattr(repo, "list_alerts_paginated")
        sig = inspect.signature(repo.list_alerts_paginated)
        params = list(sig.parameters.keys())
        assert "offset" in params
        assert "limit" in params

    @pytest.mark.asyncio
    async def test_list_alerts_paginated_returns_tuple(self, clean_database):
        """Test 4: list_alerts_paginated returns (items, total) tuple."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyAlertRepository(session_maker)

        # Act
        items, total = await repo.list_alerts_paginated(offset=0, limit=10)

        # Assert
        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total >= 0
        assert len(items) <= 10

    @pytest.mark.asyncio
    async def test_list_alerts_paginated_empty_repository(self, clean_database):
        """Test 5: Empty repository returns ([], 0)."""
        engine = get_engine()
        session_maker = create_session_maker(engine)
        repo = SqlAlchemyAlertRepository(session_maker)

        # Act
        items, total = await repo.list_alerts_paginated(offset=0, limit=10)

        # Assert - works even with empty database
        assert isinstance(items, list)
        assert items == []  # Should be empty list
        assert isinstance(total, int)
        assert total == 0  # Should be 0 for empty repository
