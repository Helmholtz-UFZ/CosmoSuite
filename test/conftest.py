"""Shared fixtures for the framework-scope tests (root test/).

The full integration/e2e harness (service orchestration, Dash app, Celery worker)
lives with the example at examples/csv_profiler/test/conftest.py. These framework
tests only need a plain logger.
"""

import logging

import pytest


@pytest.fixture
def logger():
    """A simple logger for the framework tests."""
    return logging.getLogger("cosmo_framework.tests")
