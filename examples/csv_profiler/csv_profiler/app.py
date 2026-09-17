"""Dash app for the CSV profiler example — composes the Cosmo Suite shell.

Wires the framework Job seams (config model, file validator, submit handler, app
version) to the CSV profiler domain, then builds the multi-page Dash app: the
domain workflow pages (home/input/results/job_submission) are auto-discovered from
this package's ``pages/`` folder, while the framework's infra/ops pages (logs, job
management, worker management) are imported explicitly so they register too.
"""

import logging
import logging.config
from importlib.metadata import version

import dash_bootstrap_components as dbc
from dash import Dash

from cosmo_suite.config import DEBUG, PORT
from cosmo_suite.db_manager import DbManager
from cosmo_suite.error_handling import handle_error
from cosmo_suite.files_route import serve_files
from cosmo_suite.job import Job
from cosmo_suite.layouts import app_layout
from cosmo_suite.logger import get_logger_config_web
from cosmo_suite.object_storage_manager import create_bucket, setup_remote

from csv_profiler.background_job_manager import submit_computation_job
from csv_profiler.computation_module import validate_csv
from csv_profiler.db_manager import JobTable
from csv_profiler.pydantic_models import ProfileConfig

# Wire the framework Job seams to the CSV domain BEFORE any Job is constructed
# (page callbacks build Jobs, so this must run before app.layout is set).
Job.config_model = ProfileConfig
Job.file_validator = staticmethod(validate_csv)
Job.submit_handler = staticmethod(submit_computation_job)
Job.app_version = version("csv-profiler")

# Same rule as the Job seams above: DbManager.job_table must be set on
# DbManager itself, before any framework page or Job method runs.
DbManager.job_table = JobTable

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

# Set up object storage.
setup_remote()
create_bucket()

# No Celery Beat here: it runs embedded in the worker (docker/worker.Dockerfile).
# Gunicorn with --preload imports this module once and then forks its workers; a
# thread started at import can hold one of Celery's internal locks at that moment,
# and the forked worker then blocks forever on its first task submission. Without
# --preload every worker would start its own Beat instead, and every scheduled task
# would run once per worker. See docs/conventions/celery_beat.md in cosmo-suite.

# Serve files
serve_files(app)

# Main app layout. app_layout() registers the navbar-collapse callback itself,
# since it is the thing that mounts the navbar; an app building its own navbar
# around the shared id calls layouts.register_navbar_callbacks() instead.
# with_reset=True: the input and job-submission pages offer a
# "Reset job" action, so this app opts into the framework's reset modal.
app.layout = app_layout(with_reset=True)

if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
