# What a Consumer Inherits When It Imports a Framework Page

An app registers a framework page by importing it:

```python
import cosmo_suite.pages.logs           # noqa: F401
import cosmo_suite.pages.job_management  # noqa: F401
import cosmo_suite.pages.worker_management  # noqa: F401
```

That import does far more than add a route. Dash pages register themselves, and
callbacks wire themselves, **at import time** — so the import runs code, pulls in
a transitive module graph, and claims a set of HTML ids in the app's global
callback registry.

Everything on this page has been measured in a running app. The reason it has
its own convention file is that all of it fails the same way: **no import error,
no failing test, and a symptom that surfaces somewhere else entirely.**

---

## What comes along

| Importing … | also imports | which registers |
| --- | --- | --- |
| any framework page | `cosmo_suite.layouts` | the navbar-collapse callback on `NAVBAR_TOGGLER_BUTTON_SHARED_ID` / `NAVBAR_COLLAPSE_DIV_SHARED_ID` |
| `pages.job_management` | `cosmo_suite.job`, `cosmo_suite.db_manager`, `cosmo_suite.tasks.maintenance_tasks` | its own page + three callbacks |
| `pages.worker_management` | `cosmo_suite.background_job_manager` | its own page + eleven callbacks, one of them clientside |
| `layouts.app_layout(with_reset=True)` | — | the two job-reset callbacks |

Two consequences follow from "at import time":

1. **Every seam must be set before the import.** `Job.config_model`,
   `Job.submit_handler`, `Job.app_version`, `layouts.default_wrapper_class` —
   configure them, *then* import the pages. `pages/job_management.py` builds its
   `layout` as a module-level statement, so a value set afterwards reaches the
   other two pages and silently misses that one.
2. **Order matters relative to `Dash()`.** `register_page` needs the app to
   exist, which is why the example imports the framework pages *after* the
   `Dash(...)` call rather than at the top of `app.py`.

---

## The three silent failures

### 1. A duplicate callback aborts the whole registry

If the app already registers a callback on an id that `cosmo_suite.layouts`
claims, Dash does not fail that one callback. It aborts the **entire** callback
registry, so the visible symptom is an unrelated page that has simply stopped
reacting to clicks. COSMOPOLITAN hit this in Slice 1b and resolved it by dropping
its local duplicate; COSMONAUT will meet it in Slice 2, the first time it calls
`layouts.app_layout()`.

**Rule:** before importing a framework page, check the ids in
`cosmo_suite/constants/html_ids.py` marked `SHARED` against the app's own
callbacks. A collision is resolved by removing the app's copy, not by aliasing
the id — two callbacks writing the same component is the bug, whatever it is
called.

### 2. A same-named exception makes `except` stop matching

`ObjectStorageError` exists in the framework and existed under the same name in
the app. After the switch, `except ObjectStorageError` in app code caught a class
that framework code never raises. The `except` clause is still there, still reads
correctly, and never fires again; the error escapes to the global handler and the
user gets "Internal Error" instead of the intended message.

The same trap is open today for `FileValidationError`, which the framework
defines and COSMOPOLITAN also gets from
`soil_moisture_prediction.input_file_parser` — see
[error handling](error_handling.md#exception-name-collisions-with-domain-packages).

**Rule:** when adopting a framework exception, grep for every `except <Name>` in
the app and confirm each one now refers to the framework class. Never let two
classes with one name coexist in a process; either import the framework's, or
wrap the foreign one at the boundary where it is raised.

### 3. A relative path resolves against the wrong root

`WEB_WORK_DIR` shipped as `./work_dir` in the `.env` files. Flask's
`send_from_directory` resolves a relative directory against `app.root_path` — the
*installed app package* — not against the process's working directory. Every job
file 404s, and nothing else breaks. `cosmo_suite/config.py` now absolutises the
value at import time, and the comment there records why.

**Rule:** any path a consumer configures is absolutised where the framework reads
it, not where it is used. A relative path that happens to work is a coincidence
of the container's working directory.

---

## The pattern behind all three

A name, an id, or a path is resolved **somewhere other than where it was
written**, and the wrong resolution is a legal program. Python raises nothing,
the test suite exercises neither path, and the symptom appears in a different
page, a different callback, or a different service.

When adding anything to the framework that a consumer inherits by importing —
a shared callback, an exception class, a configured path, an HTML id — ask
whether a consumer could already own that name, and whether they would find out.
If the answer is "not until a user complains", the seam belongs in this file
before it belongs in the code.
