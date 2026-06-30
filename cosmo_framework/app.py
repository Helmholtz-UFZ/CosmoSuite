"""Dash app with multiple pages."""

import logging
import logging.config
from threading import Thread

import dash_bootstrap_components as dbc
from dash import Dash

from cosmo_framework.background_job_manager import background_job_manager
from cosmo_framework.config import DEBUG, PORT
from cosmo_framework.error_handling import handle_error
from cosmo_framework.files_route import serve_files
from cosmo_framework.layouts import app_layout
from cosmo_framework.logger import get_logger_config_web
from cosmo_framework.object_storage_manager import create_bucket, setup_remote

# Configure logging BEFORE Dash() and any getLogger() calls.
logging.config.dictConfig(get_logger_config_web(DEBUG))
log = logging.getLogger(__name__)
log.debug("Web application logging configured.")

# Initialize the Dash app
app = Dash(
    __name__,
    use_pages=True,
    prevent_initial_callbacks=True,
    suppress_callback_exceptions=True,
    on_error=handle_error,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
)
server = app.server
# Start Celery Beat scheduler for periodic maintenance tasks
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
