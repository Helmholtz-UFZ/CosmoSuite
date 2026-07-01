# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

ENV PATH=$PATH:/home/appuser/rclone-binaries/
ENV TZ=Europe/Berlin

# Create non-root user early
RUN useradd -m -u 1000 appuser

# Install system dependencies
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
        git \
        libpq-dev \
        gcc \
        python3-dev \
        libc-dev \
        curl \
        unzip && \
    rm -rf /var/lib/apt/lists/*

# Install rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    unzip rclone-current-linux-amd64.zip && \
    mkdir -p /home/appuser/rclone-binaries && \
    cp rclone-*-linux-amd64/rclone /home/appuser/rclone-binaries/ && \
    chmod +x /home/appuser/rclone-binaries/rclone && \
    chown -R appuser:appuser /home/appuser/rclone-binaries && \
    rm -rf rclone-*

RUN rclone --version

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /python_docker/cosmo_template

ENV PYTHONPATH=/python_docker/cosmo_template/:/python_docker/cosmo_template/examples/csv_profiler/
ENV PATH="/python_docker/cosmo_template/.venv/bin:$PATH"

# Copy dependency files
COPY --chown=appuser:appuser . .

# Install dependencies
RUN uv sync --frozen

# Switch to non-root user
USER appuser

# Worker command
CMD echo "Starting Celery worker..."; \
    python3 /python_docker/cosmo_template/cosmo_framework/object_storage_manager.py setup_remote; \
    exec celery -A csv_profiler.celery_app.celery worker \
        --loglevel=debug \
        --concurrency=4 \
        --queues=default,computation,maintenance \
        --hostname=worker@%h \
        --without-gossip \
        --without-mingle;
