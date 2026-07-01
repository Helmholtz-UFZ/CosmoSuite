# CSV Profiler — reference domain / example app

A minimal reference application built on the [**Cosmo Framework**](../../README.md):
upload a CSV, run a background statistical-profiling job, and view the results.
It is the canonical example of how to plug a domain into the framework, and the
recommended starting point for a new Cosmo Suite app ("copy this directory").

## How it plugs into the framework

The framework `Job` is generic; this app injects the domain at startup (in both
`csv_profiler/app.py` and `csv_profiler/celery_app.py`):

```python
Job.config_model   = ProfileConfig                        # a BaseJobConfig subclass
Job.file_validator = staticmethod(validate_csv)
Job.submit_handler = staticmethod(submit_computation_job)
```

It provides the domain pieces — `ProfileConfig`, the CSV `computation_module`, the
`forms`, the workflow pages (home / input / results / job_submission), and the
Celery worker entry — while the framework provides the app shell and the infra/ops
pages (logs, job management, worker management). See
[`docs/conventions/config_model_contract.md`](../../docs/conventions/config_model_contract.md).

## Framework dependency

In this monorepo the framework is resolved from the local path (editable) via
`[tool.uv.sources]` in `pyproject.toml`, so the example always runs against the
working tree. A standalone downstream app would instead pin a git tag:

```toml
dependencies = [
    "cosmo-framework @ git+https://codebase.helmholtz.cloud/.../cosmo-framework@v0.1.0",
]
```

**Tagged-release note:** bump the pin on `main` **and tag it** before building any
image — a scheduled image build checks out the latest tag, so an untagged pin bump
would silently ship the old framework.

## Run it

```bash
uv sync                    # installs cosmo-framework (editable) + the example deps
./run_pytest.sh            # starts postgres/minio/redis and runs the test suite
./dev_up.sh                # brings the app + worker up via docker compose
```

### `--local-core` dev loop

To iterate on the framework and this app together, mount the framework source into
the running containers instead of using the installed copy (see
`docker-compose.local_pkg.yml`): mount `../../cosmo_framework` and prepend it to
`PYTHONPATH`. The mount target is the directory *containing* `cosmo_framework`.
