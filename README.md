# Cosmo Template

A working reference app that showcases the Dash + Celery + PostgreSQL + MinIO framework
used by COSMOPOLITAN and COSMONAUT. The app demonstrates how to integrate a Python
computation module into the framework using a CSV statistical profiler as the example.

## Quick Start

```bash
./dev_up.sh
```

Open http://localhost:8080 to access the application.

Use `./dev_up.sh -d` to enable debug mode (auto-reload on code changes).

## Architecture

```
Browser → Dash (Flask) → Celery worker → computation_module.py
                ↕              ↕
            PostgreSQL       MinIO
                ↕
              Redis (broker)
```

### Services (docker-compose.yml)

| Service | Image | Purpose |
|---------|-------|---------|
| `cosmo-template` | dev.Dockerfile | Dash web app (Gunicorn) |
| `cosmo-template-worker` | worker.Dockerfile | Celery worker |
| `postgres` | postgres:15 | Job metadata, logs, Celery results |
| `redis` | redis:7 | Celery message broker |
| `minio` | minio/minio | Object storage for job files |

### Data Flow

1. User uploads CSV on the job submission page
2. Job is created in PostgreSQL, CSV saved to MinIO
3. Celery worker picks up the task, downloads CSV from MinIO
4. `computation_module.py` runs the statistical profiler
5. Results (JSON) saved to MinIO, job status updated in PostgreSQL
6. Results page renders summary table, charts, and correlation heatmap

### Core Modules

| Module | Purpose |
|--------|---------|
| `computation_module.py` | CSV statistical profiler (the example computation) |
| `db_manager.py` | SQLAlchemy models: Job, LogEntry |
| `object_storage_manager.py` | MinIO file operations via rclone |
| `job.py` | Job lifecycle: create work dir, save files, sync MinIO |
| `background_job_manager.py` | Celery app config, task submission |
| `pydantic_models.py` | `ProfileConfig` — job configuration model |
| `config.py` | Environment variable loading and validation |

### Pages

| Page | Path | Purpose |
|------|------|---------|
| Home | `/` | Welcome page |
| Job Submission | `/job-submission` | Upload CSV, configure, submit |
| Results | `/results?job_id=...` | View profiling results |
| Job Management | `/job-management` | List/delete jobs |
| Logs | `/logs` | Application log viewer |
| Worker Management | `/worker-management` | Celery worker status |

## Environment Configuration

Two env files:

- `env_dev` — local Docker development
- `env_test` — local pytest (used by `run_pytest.sh`)

`dev_up.sh` copies `env_dev` to `.env` on each run.

## Testing

```bash
# Full test suite (spins up Postgres, Redis, MinIO automatically)
./run_pytest.sh

# See available flags
./run_pytest.sh --help
```

Test files in `test/`:

- `test_computation_module.py` — unit tests for `profile_csv()`
- `test_e2e.py` — Playwright end-to-end test
- `test_db_manager.py` — database operations
- `test_env.py` — environment variable completeness
- `test_html_id_enforcement.py` — HTML ID constant usage

## How to Replace the CSV Profiler With Your Own Computation

1. **Replace `computation_module.py`** with your own computation logic
2. **Update `pydantic_models.py`** — change `ProfileConfig` to your config model
3. **Update `tasks/computation_tasks.py`** — adapt the Celery task to call your module
4. **Update `pages/job_submission.py`** — adjust the upload/form for your input format
5. **Update `pages/results.py`** — display your computation's output
6. **Update tests** — replace `test_computation_module.py` with tests for your module

## Extracting Your Computation Module

When your computation module grows beyond a single file, extract it into a separate
Python package:

1. Create a new git repo with its own `pyproject.toml` (publishable to PyPI or a
   private index)
2. Add it as a dependency in this project's `pyproject.toml`
3. Activate `docker-compose.local_pkg.yml`: update it to mount your local package
   checkout into web and worker containers
4. Enable `--local-computation-module` in `dev_up.sh`: remove the error guard, wire
   it to use the compose override file

See COSMOPOLITAN's `docker-compose.local-smp.yml` and COSMONAUT's
`docker-compose.local-sr.yml` as working examples of this pattern.

## Bootstrapping a New Project

```bash
./copy.sh <new_project_name> <destination_directory>
# Example:
./copy.sh my_awesome_app /home/user/projects/my-awesome-app
```

This copies the template, renames all references, and prints a list of branded
files to customize (banner images, icons, home page text).

## Code Quality

```bash
# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## File Structure

```
src/          # Main application package
  app.py                     # Dash app initialization
  computation_module.py      # CSV statistical profiler
  db_manager.py              # SQLAlchemy models
  job.py                     # Job lifecycle management
  background_job_manager.py  # Celery configuration
  pydantic_models.py         # ProfileConfig model
  config.py                  # Environment variables
  error_handling.py          # Central error handler
  layouts.py                 # Reusable layout components
  pages/                     # Dash pages
  tasks/                     # Celery task definitions
  constants/                 # HTML IDs, general constants
  assets/                    # CSS, favicon
  static/                    # Images, icons
docker/                      # Dockerfiles
test/                        # All tests
docs/conventions/            # Coding conventions
```
