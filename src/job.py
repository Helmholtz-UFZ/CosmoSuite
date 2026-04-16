#!/usr/bin/python3
"""Module for a Cosmo Template Job."""

import base64
import json
import logging
import os
import random
import shutil
from datetime import date
from typing import Literal

import coolname
from werkzeug.utils import secure_filename

from src.background_job_manager import background_job_manager
from src.computation_module import validate_csv
from src.config import JOB_WORK_DIR_TEMPLATE
from src.constants import (
    DAYS_DELETE_NOT_SUBMITTED,
    DAYS_DELETE_SUBMITTED,
    LOG_FILE_NAME,
)
from src.db_manager import DbManager, JobTable
from src.error_handling import (
    InvalidJobID,
    JobExists,
    JobNotFound,
)
from src.object_storage_manager import (
    delete_directory_from_storage,
    delete_file_from_storage,
    get_files,
    save_files,
)
from src.pydantic_models import ProfileConfig, validate_job_id

log = logging.getLogger(__name__)

APP_VERSION = "0.1.0"
SEED = os.urandom(128)


def find_unique_job_id() -> str:
    """Find a unique job id."""
    coolname.replace_random(random.Random(SEED))

    while True:
        job_id = "_".join(coolname.generate(3))
        if not DbManager.check_existence(job_id):
            break
    return job_id


class Job:
    """This class represents a job submission by the user.

    It handles input from a web application, manages job lifecycle,
    and coordinates with background task processing.
    """

    job_id: str
    model: ProfileConfig
    start_date: date
    submitted: bool
    notified_end: bool
    logs: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    version: str
    working_dir: str

    def __init__(
        self,
        job_id=None,
        new_job_id=None,
        model=None,
    ):
        """Init class either by id, by model or make a new one."""
        if job_id is not None:
            self.job_id = job_id
            self.load()
        elif model is not None:
            self._init_from_model(model)
        else:
            self._blank_job(new_job_id)

    def __str__(self):
        """Represent class as string."""
        return self.job_id

    def load(self):
        """Load job from database and store files in working dir."""
        log.info(f"Load submission {self.job_id}")

        try:
            validate_job_id(self.job_id)
        except ValueError:
            raise InvalidJobID(self.job_id)

        log.debug(f"Job id: {self.job_id} is valid")

        for name, value in DbManager.get_job_columns(self.job_id).items():
            log.debug((f"Load column {name}"))
            if name == "input_data":
                self.model = ProfileConfig(**json.loads(value))
            setattr(self, str(name), value)

        log.debug(f"Job {self.job_id} loaded from database")

        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        get_files(self.job_id)
        log.debug(
            f"Job {self.job_id} files downloaded from object storage",
        )

    def _init_from_model(self, model):
        """Initialize job from model."""
        self.job_id = model.job_id
        self.model = model
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.logs = ""
        self.status = "PENDING"
        self.version = APP_VERSION
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        os.makedirs(self.working_dir, exist_ok=True)
        self.dump_parameters()
        self.save()

    def _blank_job(self, new_job_id):
        """Create a new job with a new job id."""
        log.info("Create new job")

        if new_job_id is None:
            job_id = find_unique_job_id()
        else:
            if DbManager.check_existence(new_job_id):
                raise JobExists(new_job_id)
            job_id = new_job_id

        self.job_id = job_id
        self.model = ProfileConfig()
        self.model.job_id = job_id
        self.start_date = date.today()
        self.submitted = False
        self.notified_end = False
        self.logs = ""
        self.status = "PENDING"
        self.version = APP_VERSION
        self.working_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=self.job_id)
        shutil.rmtree(self.working_dir, ignore_errors=True)
        os.makedirs(self.working_dir, exist_ok=True)
        self.dump_parameters()
        self.save()

    def dump_parameters(self):
        """Dump the parameters of the model to the working directory."""
        log.debug("Dump parameters to JSON file")
        with open(
            os.path.join(self.working_dir, "parameters.json"), "w", encoding="UTF-8"
        ) as f_handle:
            f_handle.write(
                self.model.model_dump_json(
                    indent=4,
                    exclude_unset=False,
                    exclude_none=True,
                    exclude_defaults=False,
                )
            )

    def delete_item(self, item_name):
        """Delete a file or folder both locally and from object storage."""
        log.debug(
            f"Delete item {item_name} from job {self.job_id}",
        )

        item_path = os.path.join(self.working_dir, item_name)
        if os.path.isfile(item_path):
            os.remove(item_path)
            delete_file_from_storage(f"{self.job_id}/{item_name}")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            delete_directory_from_storage(f"{self.job_id}/{item_name}")

    def upload_file(self, content_type, content_string, file_name):
        """Sanitize, decode, validate, and save an uploaded CSV file.

        Returns the sanitized filename on success.
        Raises FileValidationError if the file is not a valid CSV.
        """
        safe_name = secure_filename(file_name)

        if self.model.upload_file_name is not None:
            self.delete_item(self.model.upload_file_name)

        decoded = base64.b64decode(content_string)
        file_path = os.path.join(self.working_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(decoded)

        try:
            validate_csv(file_path)
        except Exception:
            os.remove(file_path)
            raise

        self.model.upload_file_name = safe_name
        self.save()
        return safe_name

    def _get_column_data(self, name):
        if name == "logs":
            log_file = os.path.join(self.working_dir, LOG_FILE_NAME)
            try:
                with open(log_file, "r") as f_handle:
                    content = f_handle.read()
                    return content.replace("\x00", "")
            except FileNotFoundError:
                return ""

        if name == "input_data":
            return self.model.model_dump_json(
                indent=4,
                exclude_unset=False,
                exclude_none=True,
                exclude_defaults=False,
            )

        return getattr(self, name)

    def reload_logs(self):
        """Reload the logs from the log file."""
        self.logs = self._get_column_data("logs")

    def save_attributes(self, attribute_list):
        """Save specific job information to the database."""
        log.debug(
            f"Save attributes {', '.join(attribute_list)} to job {self.job_id}",
        )
        data_to_insert = {name: self._get_column_data(name) for name in attribute_list}
        try:
            DbManager.update_column(self.job_id, data_to_insert)
        except JobNotFound:
            self.save()

    def save_to_db(self):
        """Save the job attributes to the database."""
        log.debug(f"Save job {self.job_id} to database")
        column_names = JobTable.__table__.columns.keys()
        data_to_insert = {name: self._get_column_data(name) for name in column_names}
        for key, value in data_to_insert.items():
            if key == "input_data":
                ProfileConfig(**json.loads(value))
        DbManager.add_entry(data_to_insert)

    def save(self):
        """Save the job files to object storage and attributes to the database."""
        log.debug(f"Save job {self.job_id}")
        save_files(self.job_id)
        self.save_to_db()

    def delete(self, delete_work_dir=True, delete_db=True):
        """Delete the job from the database and storage."""
        log.debug(f"Delete job {self.job_id}")
        if delete_work_dir:
            shutil.rmtree(self.working_dir)
        if delete_db:
            DbManager.delete_job(self.job_id)
            delete_directory_from_storage(self.job_id)

    def submit(self):
        """Submit job to Celery queue for background processing."""
        log.info(f"Submit job {self.job_id}.")

        if not DbManager.set_submitted(self.job_id):
            log.debug(f"Job {self.job_id} was already submitted.")
            return

        self.submitted = True

        # Upload files BEFORE submitting to Celery — the worker may write to
        # remote storage immediately, which would cause save_files' verification
        # to see unexpected files and fail.
        save_files(self.job_id)

        _celery_task_id, failed = background_job_manager.submit_computation_job(self)
        if failed:
            log.error(f"Job {self.job_id} failed to start.")
            self.status = "FAILED"
        else:
            self.status = "RUNNING"

        self.save_to_db()

    def time_to_life(self):
        """Return the number of days after which this job will be deleted."""
        days_passed = (date.today() - self.start_date).days
        if self.submitted:
            return DAYS_DELETE_SUBMITTED - days_passed
        else:
            return DAYS_DELETE_NOT_SUBMITTED - days_passed

    def status_color(self):
        """Return the color of the job status."""
        if self.status == "PENDING":
            return "bg-info"
        elif self.status == "RUNNING":
            return "bg-secondary"
        elif self.status == "COMPLETED":
            return "bg-success"
        elif self.status == "FAILED":
            return "bg-danger"
        else:
            return "bg-secondary"

    def reset(self):
        """Reset job to PENDING and clean all results (keeps uploaded CSV)."""
        log.info(f"Reset job {self.job_id}")
        self.status = "PENDING"
        for file in os.listdir(self.working_dir):
            if file == self.model.upload_file_name:
                continue
            self.delete_item(file)
        self.delete_logs()
        self.dump_parameters()
        self.save()

    def delete_logs(self):
        """Delete the logs."""
        log.info(f"Delete logs of job {self.job_id}")
        self.delete_item(LOG_FILE_NAME)
