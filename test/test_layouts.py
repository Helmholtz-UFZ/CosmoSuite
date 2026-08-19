"""Tests for the page-wrapper seam in ``cosmo_suite.layouts``.

The three framework pages call ``page_container_column_layout`` themselves, so a
consumer has no call site to pass ``wrapper_class`` at. Without the module-level
fallback the only hook left is ``#main-content-container``, and COSMONAUT had to
key its stylesheet on that framework-internal id.
"""

import pytest

from cosmo_suite import layouts


@pytest.fixture(autouse=True)
def reset_wrapper_class():
    """Restore the module seam — it is process-global state."""
    yield
    layouts.default_wrapper_class = None


def test_no_wrapper_div_by_default():
    """An app that sets nothing gets exactly the DOM it got before."""
    page = layouts.page_container_column_layout([])

    assert page.className == "flex-grow-1 d-flex justify-content-center g-0"


def test_module_default_wraps_pages_built_without_an_argument():
    """This is the case the three framework pages are in."""
    layouts.default_wrapper_class = "cosmonaut-page"

    page = layouts.page_container_column_layout([])

    assert page.className == "cosmonaut-page"


def test_explicit_argument_beats_the_module_default():
    """A caller that does have a call site keeps control."""
    layouts.default_wrapper_class = "cosmonaut-page"

    page = layouts.page_container_column_layout([], wrapper_class="w-100")

    assert page.className == "w-100"


def test_landing_page_layout_column_uses_the_module_default():
    """The seam reaches the landing-page helper the domain pages build on."""
    layouts.default_wrapper_class = "cosmonaut-page"

    page = layouts.landing_page_layout_column(
        "Job Submission",
        "header-div",
        "job-id-store",
        "quiet_amber_otter",
        "main-content",
    )

    assert page.className == "cosmonaut-page"
