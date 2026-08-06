# Testing

All tests live in `test/` and run against real services via Docker.

## Critical Rules for Running Tests

**ALWAYS run `./run_pytest.sh --help` before your first test execution in a session.**
The help output is the single source of truth for available flags and usage. Do not
guess flags or invent arguments — only use what `--help` shows.

**NEVER run `pytest` or `uv run pytest` directly.** Always use `./run_pytest.sh`.
The script manages `.env` backup/restore, Docker services, and cleanup. Running
pytest directly will use the wrong `.env`, skip service setup, and leave stale state.

**`--no-services` SKIPS most tests.** It passes `--no-services` to pytest, which
causes `dash_app` and `celery_worker` fixtures to call `pytest.skip()`. All e2e
tests and most module tests will be skipped. Only use it for tests that truly need
no services (`test_env`, `test_html_id_enforcement`).

**Check artifacts before rerunning.** On failure, `test/artifacts/<test-name>/`
contains screenshots, traces, HTML snapshots, server logs, and worker logs. Read
these first — they usually explain the failure without needing another run. Note
that `run_pytest.sh` clears previous artifacts by default (use `--keep-artifacts`
to preserve them across runs).

## Troubleshooting: `ModuleNotFoundError` for a package that is installed

If `run_pytest.sh` dies during collection with something like
`ImportError while loading conftest ... No module named 'redis'`, while
`uv run python -c "import redis"` in the same directory works, the venv's
console scripts are stale.

`.venv/bin/pytest` (like every console script) hardcodes an **absolute**
interpreter path in its shebang. Moving or renaming the repository directory
leaves that path pointing at an interpreter that no longer exists, and
`uv run pytest` then **silently falls through to another `pytest` on `PATH`** —
typically the one in an active `VIRTUAL_ENV` — whose `site-packages` has none of
this project's dependencies. Verified by reproduction: with a dead shebang,
`uv run pytest --version` answered the global venv's `9.0.3` instead of the
project's `8.4.2`.

Note what stays healthy and hides the problem: `uv run python` is fine, because
uv resolves that interpreter itself, so `import redis` works when you check it
by hand. Native binaries like `ruff` are fine too, so lint keeps passing while
tests cannot even collect.

Check and repair:

```bash
head -1 .venv/bin/pytest     # must point into the current repo path
rm -rf .venv && uv sync      # rewrites the shebangs
```

Both venvs need this after a move: the framework root and
`examples/csv_profiler/`.

## Code Rules

- All tests go in `test/` (flat directory, no subdirectories)
- Use constants from `src/constants/html_ids.py` for element IDs in
  Playwright locators — never literal ID strings
- All imports at top level
- When adding a required env var, update `test_env.py`'s checks

## Test Types

### E2E tests (`test_e2e.py`)

- Use Playwright via `pytest-playwright` (`page` fixture)
- App served by `dash_app` fixture (werkzeug make_server in background thread)
- Require all services: Postgres, Redis, MinIO, Celery worker
- Test full user workflows through the browser
- Reusable helpers in `test/help_functions_tests.py`

### Module tests (everything else)

Service requirements vary by test:

| Test file | Services needed |
|-----------|----------------|
| `test_computation_module.py` | None (unit test, pandas only) |
| `test_db_manager.py` | Postgres |
| `test_env.py` | None (reads env files only) |
| `test_html_id_enforcement.py` | None (checks source code only) |

## Fixtures (`conftest.py`)

- `pytest_configure()` verifies all services are reachable before any tests run (gated by `--no-services`)
- `dash_app` (session) — starts the Dash app via werkzeug make_server in a background thread, polls until responsive, shuts down cleanly
- `page` (function) — wraps pytest-playwright's page fixture; captures HTML, console logs, server logs, and worker logs on failure
- `celery_worker` (session) — starts a real Celery worker subprocess with log capture, terminates on teardown
- `logger` — configured logger with suppressed third-party noise

## Artifacts

Playwright artifacts are stored in `test/artifacts/` and include:
- **Screenshots** (`--screenshot only-on-failure`): browser screenshots on test failure
- **Traces** (`--tracing retain-on-failure`): Playwright traces viewable with `npx playwright show-trace`
- **HTML snapshots**: rendered DOM at failure time
- **Console logs**: browser console messages
- **Server logs**: Python server-side logs (callbacks, validation errors, file operations)
- **Worker logs**: Celery worker output

**Which artifact to check first:**

| Failure type | Check first |
|---|---|
| Element not found / timeout | `test-failed-1.png` — is the element on screen? |
| Callback race / stuck overlay | `trace.zip` — step through the action timeline |
| JavaScript error | `console.log` — browser-side errors |
| Unexpected app behavior | `server.log` — Dash callback logs and exceptions |
| Background task failure | `worker.log` — Celery worker output and task traces |
| Layout / rendering issue | `page.html` — inspect the DOM structure |

## CI Pipeline

Not yet configured for this template. Add CI configuration as needed for your
project.

## Examples

### Do

```python
from playwright.sync_api import expect

from src.constants.html_ids import SOME_BUTTON_ID

def test_something(page, dash_app):
    page.goto(f"http://localhost:{PORT}/")
    page.locator(f"#{SOME_BUTTON_ID}").click()
    expect(page.locator(f"#{SOME_BUTTON_ID}")).to_be_visible()
```

### Don't

```python
def test_something(page, dash_app):
    page.locator("#some_button").click()  # Never use literal ID strings
```

## Notes

- `check_all_errors(page)` in `test/help_functions_tests.py` is the standard post-action verification — checks console errors, JS errors, and broken images
- Use `locator.scroll_into_view_if_needed()` before clicking elements that may be off-screen
