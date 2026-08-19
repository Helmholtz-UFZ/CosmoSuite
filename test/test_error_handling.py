"""Tests for the ``on_unhandled`` hook on ``handle_error``.

The hook exists so an app can be notified about unexpected errors — both apps
mail their maintainer — without the framework importing an email service. The
failure it guards against is silent: swapping an app's own ``handle_error`` for
the framework's would switch those mails off with no import error and no failing
test, which is exactly why the behaviour is pinned down here.
"""

import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict
from werkzeug.exceptions import NotFound

from cosmo_suite.constants import (
    ERROR_MESSAGE_DIV_SHARED_ID,
    ERROR_MODAL_SHARED_ID,
    ERROR_TITLE_DIV_SHARED_ID,
)
from cosmo_suite.error_handling import InvalidJobID, JobNotFound, handle_error


class Recorder:
    """Callable that records the exceptions it was handed."""

    def __init__(self, raises=None):
        """Store an optional exception the recorder raises when called."""
        self.calls = []
        self.raises = raises

    def __call__(self, error):
        """Record the error, then raise if this recorder was built to fail."""
        self.calls.append(error)
        if self.raises is not None:
            raise self.raises


@pytest.fixture
def callback_ctx():
    """Install the Dash callback context ``handle_error`` runs inside.

    Dash calls ``on_error`` from within a callback, where ``dash.ctx`` and
    ``set_props`` are available; outside one both raise
    MissingCallbackContextException. The fixture provides the same context Dash
    would and yields it, so a test can assert on the props that were set.
    """
    ctx = AttributeDict(triggered_inputs=[], updated_props={})
    token = context_value.set(ctx)
    yield ctx
    context_value.reset(token)


def test_hook_called_for_unexpected_error(callback_ctx):
    """An error outside the expected set reaches the hook."""
    notify = Recorder()
    error = ValueError("something nobody planned for")

    handle_error(error, on_unhandled=notify)

    assert notify.calls == [error]


@pytest.mark.parametrize(
    "error",
    [JobNotFound("no_such_job"), InvalidJobID("../etc/passwd"), NotFound()],
)
def test_hook_not_called_for_expected_errors(callback_ctx, error):
    """Errors the app handles by design must not page the maintainer."""
    notify = Recorder()

    handle_error(error, on_unhandled=notify)

    assert notify.calls == []


def test_expected_error_still_opens_the_modal(callback_ctx):
    """Skipping the hook does not skip the user-facing modal."""
    handle_error(JobNotFound("no_such_job"), on_unhandled=Recorder())

    assert callback_ctx.updated_props[ERROR_MODAL_SHARED_ID]["is_open"] is True
    assert callback_ctx.updated_props[ERROR_TITLE_DIV_SHARED_ID]["children"] == (
        "Job Not Found"
    )


def test_without_hook_behaves_as_before(callback_ctx):
    """The v0.4.1 call signature keeps working — the parameter is additive."""
    handle_error(ValueError("boom"))

    assert callback_ctx.updated_props[ERROR_MODAL_SHARED_ID]["is_open"] is True
    assert callback_ctx.updated_props[ERROR_TITLE_DIV_SHARED_ID]["children"] == (
        "Internal Error"
    )


def test_dispatch_is_by_exact_type_not_isinstance(callback_ctx):
    """A subclass of a mapped exception falls back to the generic entry.

    The lookup is a dict hit on ``type(error)``, never an isinstance walk, so a
    subclass does not inherit its parent's title. Pinned because it is the kind
    of thing a later refactor changes by accident: a mapped subclass would start
    reporting a different modal title with nothing else failing.
    """

    class UnmappedJobNotFound(JobNotFound):
        pass

    handle_error(UnmappedJobNotFound("no_such_job"))

    assert callback_ctx.updated_props[ERROR_TITLE_DIV_SHARED_ID]["children"] == (
        "Internal Error"
    )


def test_failing_hook_does_not_swallow_the_modal(callback_ctx):
    """A broken notifier must not hide the error it was reporting."""
    notify = Recorder(raises=RuntimeError("SMTP unreachable"))

    handle_error(ValueError("boom"), on_unhandled=notify)

    assert notify.calls  # the hook did run
    assert callback_ctx.updated_props[ERROR_MODAL_SHARED_ID]["is_open"] is True
    assert ERROR_MESSAGE_DIV_SHARED_ID in callback_ctx.updated_props
