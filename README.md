# Cosmo Framework

The shared **Dash + Celery + PostgreSQL + MinIO** application framework for the Cosmo
Suite (sister apps [COSMOPOLITAN](../cosmopolitan) and [COSMONAUT](../ufz-cosmonaut)).
The framework owns the *workflow machinery* — the app shell, job lifecycle, Celery
wiring, object storage, logging, error handling, and the infra/ops pages — while a
**domain** provides *what flows through it* (its config model, computation, forms, and
workflow pages).

This repo is the framework's home. It also ships a reference domain,
[`examples/csv_profiler/`](examples/csv_profiler/) — a CSV statistical profiler — that
depends on the framework and is the recommended starting point for a new app.

## Repo layout

```
cosmo-framework/
├── cosmo_framework/        # the published package (domain-free) — the wheel
├── examples/csv_profiler/  # reference domain: depends on the framework, NOT in the wheel
│   ├── csv_profiler/        # the example's Python package (app, ProfileConfig, pages, …)
│   ├── docker/  docker-compose.yml  dev_up.sh  run_pytest.sh  env_*  # its runtime
│   └── test/                # the integration/e2e suite
├── test/                   # framework-scope tests (html-id enforcement)
├── docs/                   # design docs + conventions
└── pyproject.toml          # name = "cosmo-framework"; wheel packages = ["cosmo_framework"]
```

## Consuming the framework

Apps consume `cosmo-framework` as a **pinned git-tag dependency** (not a clone), the
way `dash_form_factory` is already shared across the suite:

```toml
[project]
dependencies = [
    "cosmo-framework @ git+https://codebase.helmholtz.cloud/.../cosmo-framework@v0.1.0",
]
```

Auth uses `CI_JOB_TOKEN` / SSH; `uv` locks the resolved commit. A domain plugs itself
into the framework by injecting three `Job` seams at startup — see the
[config-model contract](docs/conventions/config_model_contract.md).

### Start a new app

Copy `examples/csv_profiler/` as your starting point, replace the domain pieces
(`ProfileConfig`, `computation_module`, `forms`, workflow pages, computation task), and
point the `cosmo-framework` dependency at a released tag.

### `--local-core` dev loop

To develop the framework and an app together, mount the framework source into the
running containers instead of using the installed copy (see
`examples/csv_profiler/docker-compose.local_pkg.yml`): mount `../../cosmo_framework`
and prepend it to `PYTHONPATH`. The mount target is the directory *containing*
`cosmo_framework`. Within this monorepo the example already resolves the framework from
the local path (`[tool.uv.sources]` in the example's `pyproject.toml`), so
`uv sync` in `examples/csv_profiler/` runs it against the working tree.

### Releasing (two-step, tagged)

1. Publish the framework: bump `version` in `pyproject.toml` and tag it on `main`.
2. Bump the `cosmo-framework` pin in each consumer's `pyproject.toml` **and** `uv.lock`.

**The pin bump must land on `main` and be tagged before any image build** — a scheduled
`build-latest-tag` checks out the latest tag, so an untagged bump would silently ship
the old framework.

## Framework vs domain (Phase 1)

The framework owns the **shell + infra/ops pages** and the job/task machinery; the
**workflow pages** stay domain-side until the Layer-B page/result seam:

| Framework (`cosmo_framework/`)                                   | Domain (`examples/csv_profiler/`)                    |
| ---------------------------------------------------------------- | ---------------------------------------------------- |
| `job.py` (generic `Job` + 3 injected seams), `layouts.py` (shell)| `app.py` (composes shell + wires seams), `forms.py`  |
| `background_job_manager.py`, `celery_app.py`/`celery_config.py`  | `pydantic_models.py` (`ProfileConfig`), `computation_module.py` |
| `config`, `db_manager`, `object_storage_manager`, `logger`, errors | `tasks/computation_tasks.py`, domain constants     |
| pages: `logs`, `job_management`, `worker_management`             | pages: `home`, `input`, `results`, `job_submission`  |

The framework package is kept **domain-free** — a CI gate fails if any CSV-profiler
reference appears under `cosmo_framework/`.

## Running the example

```bash
cd examples/csv_profiler
uv sync                      # framework (editable, local path) + example deps
./dev_up.sh                  # app + worker via docker compose  →  http://localhost:8080
./run_pytest.sh              # starts postgres/minio/redis and runs the suite
```

## Testing

- **Framework:** `uv run pytest test/` at the repo root (static id enforcement); plus
  the `ruff` lint and the domain-free grep gate (`.gitlab-ci.yml`).
- **Example (integration + e2e):** from `examples/csv_profiler/`, `./run_pytest.sh`.

## Conventions & design

See [`docs/conventions/`](docs/conventions/) and the design docs in
[`docs/plan/`](docs/plan/) (`framework-generalization.md`,
`cosmo-core-package-boundary.md`).
