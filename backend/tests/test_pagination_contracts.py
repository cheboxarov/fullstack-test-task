"""Tests for pagination contracts per D-01, D-02, D-04."""

import inspect

import pytest
from src.application.ports import AlertRepository, FileRepository
from src.presentation.schemas import PaginatedResponse, FileItem


class TestPaginatedResponse:
    """Test suite for PaginatedResponse generic model."""

    def test_paginated_response_can_be_instantiated(self):
        """Test 1: PaginatedResponse[FileItem] can be instantiated with items, total=100, page=1, page_size=10."""
        # Arrange
        items = []
        total = 100
        page = 1
        page_size = 10

        # Act
        response = PaginatedResponse[FileItem](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

        # Assert
        assert response.items == items
        assert response.total == total
        assert response.page == page
        assert response.page_size == page_size

    def test_pages_calculates_correctly(self):
        """Test 2: PaginatedResponse.pages calculates correctly (ceil(total/page_size))."""
        # Test various scenarios
        test_cases = [
            # (total, page_size, expected_pages)
            (100, 10, 10),  # Exact division
            (95, 10, 10),  # Rounds up
            (101, 10, 11),  # One extra page
            (5, 10, 1),  # Less than one page
            (0, 10, 0),  # Empty
        ]

        for total, page_size, expected_pages in test_cases:
            response = PaginatedResponse[FileItem](
                items=[],
                total=total,
                page=1,
                page_size=page_size,
            )
            assert response.pages == expected_pages, (
                f"Failed for total={total}, page_size={page_size}"
            )


class TestRepositoryProtocols:
    """Test suite for repository pagination protocol methods."""

    def test_file_repository_has_list_files_paginated(self):
        """Test 3: FileRepository protocol includes list_files_paginated(offset, limit) signature."""
        # Check that the protocol has the method
        assert hasattr(FileRepository, "list_files_paginated")

        # Check signature includes offset and limit
        sig = inspect.signature(FileRepository.list_files_paginated)
        params = list(sig.parameters.keys())
        assert "offset" in params
        assert "limit" in params

    def test_alert_repository_has_list_alerts_paginated(self):
        """Test 4: AlertRepository protocol includes list_alerts_paginated(offset, limit) signature."""
        # Check that the protocol has the method
        assert hasattr(AlertRepository, "list_alerts_paginated")

        # Check signature includes offset and limit
        sig = inspect.signature(AlertRepository.list_alerts_paginated)
        params = list(sig.parameters.keys())
        assert "offset" in params
        assert "limit" in params
