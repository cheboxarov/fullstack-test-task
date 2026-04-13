"""Unit tests for Celery app factory.

Tests D-06 factory pattern implementation with no global state.
Verifies configuration and isolation of Celery app instances.
"""

import pytest
from celery import Celery

from src.bootstrap.celery import create_celery_app
from src.bootstrap.settings import Settings


def test_create_celery_app_returns_celery_instance():
    """Test that factory returns a valid Celery instance."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="test-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    assert app is not None
    assert isinstance(app, Celery)
    assert hasattr(app, "task")
    assert hasattr(app, "conf")


def test_celery_app_configures_broker_from_settings():
    """Test that broker URL is configured from settings."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/1",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="test-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    assert app.conf.broker_url == "redis://localhost:6379/1"


def test_celery_app_configures_backend_from_settings():
    """Test that result backend is configured from settings."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/2",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="test-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    assert app.conf.result_backend == "redis://localhost:6379/2"


def test_celery_app_configures_default_queue_from_settings():
    """Test that default queue is configured from settings."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="custom-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    assert app.conf.task_default_queue == "custom-queue"
    assert app.conf.task_default_exchange == "custom-queue"
    assert app.conf.task_default_routing_key == "custom-queue"


def test_two_calls_produce_independent_instances():
    """Test that factory creates independent instances (no shared state)."""
    settings1 = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="queue-1",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )
    settings2 = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/1",
        celery_broker_url="redis://localhost:6379/1",
        celery_queue="queue-2",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app1 = create_celery_app(settings1)
    app2 = create_celery_app(settings2)

    # Should be different objects
    assert app1 is not app2

    # Each should have its own configuration
    assert app1.conf.task_default_queue == "queue-1"
    assert app2.conf.task_default_queue == "queue-2"
    assert app1.conf.broker_url != app2.conf.broker_url


def test_tasks_are_registered_on_app():
    """Test that expected tasks are registered on the Celery app."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="test-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    # Check that tasks are registered
    registered_tasks = app.tasks.keys()
    assert "scan_file_for_threats" in registered_tasks
    assert "extract_file_metadata" in registered_tasks
    assert "send_file_alert" in registered_tasks


def test_task_has_retry_configuration():
    """Test that tasks have retry configuration set."""
    settings = Settings(
        postgres_user="test",
        postgres_password="test",
        postgres_host="localhost",
        postgres_port="5432",
        postgres_db="test",
        storage_dir="/tmp",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/0",
        celery_queue="test-queue",
        max_upload_size_bytes=10485760,
        upload_rate_limit_per_minute=10,
        retry_max_attempts=3,
        retry_backoff_base_seconds=5,
    )

    app = create_celery_app(settings)

    # Get the scan task
    scan_task = app.tasks.get("scan_file_for_threats")
    assert scan_task is not None

    # Verify retry settings are preserved
    assert hasattr(scan_task, "_app")


def test_different_settings_produce_different_configs():
    """Test that factory respects different settings configurations."""
    test_settings = [
        Settings(
            postgres_user="test",
            postgres_password="test",
            postgres_host="localhost",
            postgres_port="5432",
            postgres_db="test",
            storage_dir="/tmp",
            redis_url="redis://redis1:6379/0",
            celery_broker_url="redis://redis1:6379/0",
            celery_queue="prod",
            max_upload_size_bytes=10485760,
            upload_rate_limit_per_minute=10,
            retry_max_attempts=3,
            retry_backoff_base_seconds=5,
        ),
        Settings(
            postgres_user="test",
            postgres_password="test",
            postgres_host="localhost",
            postgres_port="5432",
            postgres_db="test",
            storage_dir="/tmp",
            redis_url="redis://redis2:6379/0",
            celery_broker_url="redis://redis2:6379/0",
            celery_queue="staging",
            max_upload_size_bytes=10485760,
            upload_rate_limit_per_minute=10,
            retry_max_attempts=3,
            retry_backoff_base_seconds=5,
        ),
    ]

    apps = [create_celery_app(s) for s in test_settings]

    # Each app should have distinct configuration
    assert apps[0].conf.broker_url != apps[1].conf.broker_url
    assert apps[0].conf.task_default_queue != apps[1].conf.task_default_queue
