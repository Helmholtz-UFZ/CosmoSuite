"""Celery application with task registration.

This module creates the Celery worker entry point by importing the shared
Celery app and registering all task functions. The worker command points here:

    celery -A src.celery_app.celery worker ...

Separated from background_job_manager to break a circular import:
    tasks/*.py → job → background_job_manager → tasks/*.py
"""

from src.background_job_manager import (
    NAME_CLEANUP_TASK,
    NAME_COMPUTATION_TASK,
    NAME_TEST_TASK,
    background_job_manager,
)
from src.tasks.computation_tasks import start_computation_task
from src.tasks.maintenance_tasks import cleanup_task
from src.tasks.test_tasks import long_running_test_task

app = background_job_manager.app

app.task(bind=True, name=NAME_COMPUTATION_TASK)(start_computation_task)
app.task(bind=True, name=NAME_CLEANUP_TASK)(cleanup_task)
app.task(bind=True, name=NAME_TEST_TASK)(long_running_test_task)

# Expose for: celery -A src.celery_app.celery worker ...
celery = app
