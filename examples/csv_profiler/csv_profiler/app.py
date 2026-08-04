"""Dash app for the CSV profiler example — composes the Cosmo Suite shell.

Wires the framework Job seams (config model, file validator, submit handler) to
the CSV profiler domain, then builds the multi-page Dash app: the domain workflow
pages (home/input/results/job_submission) are auto-discovered from this package's
``pages/`` folder, while the framework's infra/ops pages (logs, job management,
worker management) are imported explicitly so they register too.
"""

import logging
import logging.config
from threading import Thread

import dash_bootstrap_components as dbc
from dash import Dash

from cosmo_suite.background_job_manager import background_job_manager
from cosmo_suite.config import DEBUG, PORT
from cosmo_suite.error_handling import handle_error
from cosmo_suite.files_route import serve_files
from cosmo_suite.job import Job
from cosmo_suite.layouts import app_layout
from cosmo_suite.logger import get_logger_config_web
from cosmo_suite.object_storage_manager import create_bucket, setup_remote

from csv_profiler.background_job_manager import submit_computation_job
from csv_profiler.computation_module import validate_csv
from csv_profiler.pydantic_models import ProfileConfig

# Wire the framework Job seams to the CSV domain BEFORE any Job is constructed
# (page callbacks build Jobs, so this must run before app.layout is set).
Job.config_model = ProfileConfig
Job.file_validator = staticmethod(validate_csv)
Job.submit_handler = staticmethod(submit_computation_job)

# Configure logging BEFORE Dash() and any getLogger() calls.
logging.config.dictConfig(get_logger_config_web(DEBUG))
log = logging.getLogger(__name__)
log.debug("Web application logging configured.")

# Initialize the Dash app (domain pages auto-discovered from ./pages/)
app = Dash(
    __name__,
    use_pages=True,
    prevent_initial_callbacks=True,
    suppress_callback_exceptions=True,
    on_error=handle_error,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
)
server = app.server

# Register the framework's infra/ops pages (they live in the installed package,
# not under this app's pages_folder). register_page requires the app to exist
# first, so these imports run after Dash().
import cosmo_suite.pages.logs  # noqa: E402, F401
import cosmo_suite.pages.job_management  # noqa: E402, F401
import cosmo_suite.pages.worker_management  # noqa: E402, F401

# Set up object storage and start the Celery Beat scheduler.
setup_remote()
create_bucket()


def start_beat_scheduler():
    """Start Celery Beat scheduler with thread-specific logging."""
    beat = background_job_manager.app.Beat(loglevel="DEBUG")
    beat.run()


# Start Beat scheduler as daemon thread
beat_thread = Thread(target=start_beat_scheduler, daemon=True)
beat_thread.start()
log.info("Celery Beat scheduler started in background thread")

# Serve files
serve_files(app)

# Main app layout
app.layout = app_layout()

if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
