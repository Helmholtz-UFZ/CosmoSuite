# Convention: the config-model contract (`BaseJobConfig`)

A `cosmo_framework` `Job` is generic over its configuration `model`. A domain
plugs its configuration into the framework by injecting three class attributes on
`Job` at application startup — in **both** the web app (`app.py`) and the Celery
worker entrypoint (`celery_app.py`), **before any `Job` is constructed**:

```python
Job.config_model   = ProfileConfig                        # a BaseJobConfig subclass
Job.file_validator = staticmethod(validate_csv)           # optional; None = no-op
Job.submit_handler = staticmethod(submit_computation_job)
```

## The `config_model` contract

`Job.config_model` MUST be a subclass of
`cosmo_framework.pydantic_models.BaseJobConfig`. `BaseJobConfig` provides the two
fields the framework `Job` relies on generically:

- **`job_id: str`** — validated by `validate_job_id`; the job's identity.
- **`upload_file_name: str | None`** — the single uploaded input file the `Job`
  tracks (used by `Job.upload_file` and `Job.reset`).

A domain config model adds its own fields on top (the CSV profiler example adds
`handle_missing`, `histogram_bins`, `compute_correlation`, …).

`Job.config_model` is **fail-loud**: it defaults to `None`, and constructing a
`Job` without setting it raises `RuntimeError`. `file_validator` may stay `None`
(no-op); `submit_handler` fails loud only when `Job.submit()` is actually called.

## Why injection, not import

Injecting the config model (rather than importing it) is what keeps
`cosmo_framework` domain-free: the package never imports the domain, and CI
enforces this with a grep gate. This is the Phase-1 minimal seam; the full
`DomainPlugin` protocol/registry is Layer B (see
`docs/plan/cosmo-core-package-boundary.md`).
