"""Event loop utilities for worker tasks.

This module provides run_in_worker_loop to avoid circular imports between
tasks.py and container.py.
"""

import asyncio
from collections.abc import Awaitable

_worker_loop: asyncio.AbstractEventLoop | None = None


def run_in_worker_loop(coroutine: Awaitable[object]) -> object:
    """Run an async coroutine in the worker event loop.

    Creates a new event loop if one doesn't exist or is closed.
    This is used in Celery worker context where we need to run
    async code synchronously.

    Args:
        coroutine: The async coroutine to run

    Returns:
        The result of the coroutine
    """
    global _worker_loop

    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coroutine)
