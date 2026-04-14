"""Error handling utilities for Dash apps."""

import json
import logging
import traceback

import dash
import dash_bootstrap_components as dbc
import psycopg2
from dash import set_props
from sqlalchemy.exc import DatabaseError, OperationalError
from werkzeug.exceptions import NotFound

from src.constants import (
    ERROR_MESSAGE_DIV_SHARED_ID,
    ERROR_MODAL_SHARED_ID,
    ERROR_TITLE_DIV_SHARED_ID,
    LOADING_OVERLAY_MODAL_SHARED_ID,
)
from src.object_storage_manager import ObjectStorageError

log = logging.getLogger(__name__)


class InvalidJobID(Exception):
    """Raised by Job if init with invalid job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} is not a valid job_id.")


class JobExists(Exception):
    """Raised by Job if a new job is created with an existing job id."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"{job_id} already exists.")


class JobNotFound(Exception):
    """Custom exception for when a job is not found."""

    def __init__(self, job_id):
        """Add job id as attribute and format error message."""
        self.job_id = job_id
        super().__init__(f"Job with ID '{job_id}' not found")


class WorkerManagementError(Exception):
    """Base exception for worker management operations."""

    ...


class TaskNotFoundError(WorkerManagementError):
    """Raised when task cannot be found."""

    ...


class WorkerNotAvailableError(WorkerManagementError):
    """Raised when no workers are available."""

    ...


class RedisConnectionError(WorkerManagementError):
    """Raised when Redis/Celery broker is unavailable."""

    ...


class FileValidationError(Exception):
    """Raised when an uploaded file fails validation."""

    ...


database_error_title = "Database Connection Error"
database_error_message = "Unfortunately, it is not possible to connect to the job database. Please try again later."  # noqa
error_responds_dict = {
    psycopg2.DatabaseError: (
        database_error_title,
        database_error_message,
    ),
    DatabaseError: (
        database_error_title,
        database_error_message,
    ),
    OperationalError: (
        database_error_title,
        database_error_message,
    ),
    ObjectStorageError: (
        database_error_title,
        database_error_message,
    ),
    NotFound: ("File Not Found", "The file could not be found."),
    Exception: ("Internal Error", "Ups this should not happen. An error occurred."),
    JobNotFound: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit job submission to make a new submission.",
    ),
    InvalidJobID: (
        "Job Not Found",
        "Could not find the job '{job_id}'. Visit job submission to make a new submission.",
    ),
    WorkerNotAvailableError: (
        "No Workers Available",
        "No Celery workers are currently running. Please check the worker service status.",  # noqa
    ),
    TaskNotFoundError: (
        "Task Not Found",
        "The selected task could not be found. It may have already completed or been cancelled.",  # noqa
    ),
    RedisConnectionError: (
        "Background Service Unavailable",
        "The background job service is temporarily unavailable. Please try again later.",  # noqa
    ),
    JobExists: (
        "Job Already Exists",
        "A job with ID '{job_id}' already exists. Please use a different job ID.",
    ),
    # FileValidationError is always caught by the upload callback and shown
    # inline. If it reaches the global handler, something is wrong — treat
    # it as undefined behaviour and show the generic internal error.
    FileValidationError: (
        "Internal Error",
        "Ups this should not happen. An error occurred.",
    ),
}
error_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Error"),
            id=ERROR_TITLE_DIV_SHARED_ID,
            close_button=False,
            className="bg-light",
        ),
        dbc.ModalBody(id=ERROR_MESSAGE_DIV_SHARED_ID, className="text-danger bg-light"),
        dbc.ModalFooter(className="bg-light"),
    ],
    id=ERROR_MODAL_SHARED_ID,
    is_open=False,
)


def _truncate_string(value, max_length=200, head_length=100, tail_length=50):
    """Truncate a string if it exceeds max_length."""
    if not isinstance(value, str):
        return value
    if len(value) <= max_length:
        return value
    return f"{value[:head_length]}...{value[-tail_length:]}"


def _truncate_data(data):
    """Recursively truncate long strings in data structures."""
    if isinstance(data, dict):
        return {key: _truncate_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_truncate_data(item) for item in data]
    elif isinstance(data, str):
        return _truncate_string(data)
    else:
        return data


def handle_error(error):
    """Handle the error and return a formatted message."""
    log.debug(f"Error: {error}")

    if not isinstance(
        error,
        (
            NotFound,
            JobNotFound,
            InvalidJobID,
        ),
    ):
        callback_context = dash.ctx
        truncated_triggered = _truncate_data(callback_context.triggered)
        log.error(f"Unhandled error: {error}")
        log.error(
            f"Traceback info: {traceback.format_exc()}\n\n"
            f"Input info: {json.dumps(truncated_triggered)}"
        )

    # dispatch lookup: unknown exception types fall back to the generic Exception entry
    error_title = error_responds_dict.get(type(error), error_responds_dict[Exception])[
        0
    ]
    error_message = error_responds_dict.get(
        type(error), error_responds_dict[Exception]
    )[1]

    try:
        error_message = error_message.format(job_id=error.job_id)
    except AttributeError:
        pass

    log.error(f"{error_title}: {error_message}")
    log.error(f"Error details: {traceback.format_exc()}")
    set_props(LOADING_OVERLAY_MODAL_SHARED_ID, {"is_open": False})
    set_props(ERROR_MODAL_SHARED_ID, {"is_open": True})
    set_props(ERROR_TITLE_DIV_SHARED_ID, {"children": error_title})
    set_props(ERROR_MESSAGE_DIV_SHARED_ID, {"children": error_message})
