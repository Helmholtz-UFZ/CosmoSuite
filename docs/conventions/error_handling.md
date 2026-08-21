# Error Handling Conventions

## Central Error Handler

All error handling is centralized in `src/error_handling.py`.

---

## Adding New Errors

1. **Define custom exception class** in `error_handling.py`:
   ```python
   class MyCustomError(Exception):
       def __init__(self, some_id):
           self.some_id = some_id
           super().__init__(f"Error with {some_id}")
   ```

2. **Add to `error_responds_dict`** with user-friendly message:
   ```python
   error_responds_dict = {
       MyCustomError: ("Error Title", "User-friendly message about {some_id}"),
       # ...
   }
   ```

3. **Decide on severity** - should error be logged at ERROR level?

---

## Existing Custom Exceptions

- `JobNotFound(job_id)` - Job not in database
- `WrongCeleryTaskId(task_id)` - Invalid Celery task ID
- `JobTableNotConfigured()` - `DbManager.job_table` was never assigned; see
  [database schema](database_schema.md#jobcolumns-the-framework-supplies-columns-the-app-supplies-the-table)

---

## Error Modal

User-facing errors display in modal dialog:
- `ERROR_MODAL_SHARED_ID` - Main modal
- `ERROR_MODAL_TITLE_SHARED_ID` - Title section
- `ERROR_MODAL_MESSAGE_SHARED_ID` - Message body

---

## Integration with Dash

`handle_error()` function integrates with Dash's `on_error`:

```python
# In app.py
app = Dash(..., on_error=handle_error)
```

Flow:
1. Log error at DEBUG level
2. Check if custom error - log at ERROR with context
3. Unhandled errors: log traceback, then call `on_unhandled` if one was given
4. Extract error info for user message
5. Display modal via `set_props()`

---

## Notifying someone: the `on_unhandled` hook

```python
def handle_error(error, *, on_unhandled: Callable[[Exception], None] | None = None) -> None
```

Both apps mail their maintainer when an unexpected error reaches the global
handler. The framework does **not** send that mail. It calls a callable the app
hands it:

```python
# In app.py
from functools import partial
from cosmo_suite.error_handling import handle_error

from my_app.email_service import notify_maintainer

app = Dash(..., on_error=partial(handle_error, on_unhandled=notify_maintainer))
```

Three properties of this seam are deliberate, and each one is load-bearing:

- **`error_handling` never imports an email service.** That would pull mail
  configuration into the framework's dependency set and close an import cycle
  back into the app. The framework calls what it is given and knows nothing
  about it.
- **Keyword-only.** Existing `handle_error(e)` call sites and
  `Dash(on_error=handle_error)` keep working untouched, so the addition is safe
  for a consumer still pinned to an older tag.
- **The hook fires only for unexpected errors** — the same set that gets a full
  traceback logged. `JobNotFound`, `InvalidJobID` and `NotFound` are handled by
  design and must not page anyone.

A hook that raises is logged and swallowed. This is a deliberate deviation from
the no-bare-`except` rule (`cosmo_suite/error_handling.py` carries the comment):
an SMTP timeout must not take the user's error modal down with it.

**Why this hook exists at all:** without it, an app that adopts the framework's
`handle_error` switches its maintainer mails off *silently*. No import error, no
failing test, just mails that stop arriving. See
[framework page imports](framework_page_imports.md) for the other members of that
family.

---

## Exception-name collisions with domain packages

`FileValidationError` is defined by the framework **and** arrives in COSMOPOLITAN
from `soil_moisture_prediction.input_file_parser`. Two classes, one name, in one
process.

**Decision (Slice 2):** the framework keeps defining
`cosmo_suite.error_handling.FileValidationError`. It is in `error_responds_dict`
and the upload callbacks catch it, so it stays where it is. Resolving the
collision is app-side work and belongs in the consuming app's own plan; the app
either catches both classes explicitly, or wraps the foreign exception into the
framework's at the upload boundary where it is raised.

**What must not happen:** shadowing one import with the other. The `except`
clause in the upload callback keeps compiling and silently stops matching, so the
validation error escapes to the global handler and the user is shown "Internal
Error" instead of what is wrong with their file.

---

## Callback Error Patterns

### Inline validation errors
Return error message in callback output:
```python
@callback(...)
def validate_input(value):
    try:
        result = validate(value)
    except ValueError as e:
        return (dash.no_update, str(e), True)  # error message, disable button
    return (result, "", False)
```

### Guard conditions
Use `PreventUpdate` to stop execution:
```python
@callback(...)
def process_action(n_clicks, job_id):
    if n_clicks is None:
        raise PreventUpdate

    if job.status != JOB_STATUS_PENDING:
        log.warning(f"Cannot process - job status is {job.status}")
        raise PreventUpdate
```

### Background task errors
Update status on failure:
```python
try:
    # process
    job.model.status = JOB_STATUS_COMPLETED
except Exception as e:
    log.error(f"Error: {e}", exc_info=True)
    job.model.status = JOB_STATUS_FAILED
    raise
finally:
    job.save()
```
