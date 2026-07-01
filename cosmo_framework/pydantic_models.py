"""Framework pydantic models: job-id validation + the base job-config contract.

`BaseJobConfig` is the contract for a Job's `model`. A domain provides a config
model that subclasses it (adding its own fields) and injects it via
`Job.config_model` at startup. Every domain config model therefore carries the
generic `job_id` and `upload_file_name` fields the framework `Job` relies on to
persist, reload, and track the single uploaded input file without knowing the
domain. See docs/plan/cosmo-core-package-boundary.md (config-model contract).
"""

import logging
import re
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

log = logging.getLogger(__name__)


def validate_job_id(job_id: str) -> str:
    """Validate job id.

    Job IDs must contain only letters, numbers, or underscores,
    and be between 8 and 50 characters long.
    """
    log.debug(f"Check job id {job_id}")

    job_id_regex = r"^\w+$"
    if not re.match(job_id_regex, job_id):
        raise ValueError("Job id must contain only letters numbers or underscore")

    min_job_id_length = 8
    max_job_id_length = 50

    if len(job_id) < min_job_id_length or len(job_id) > max_job_id_length:
        raise ValueError(
            f"Job id must be between {min_job_id_length} and {max_job_id_length} characters"  # noqa
        )
    return job_id


class BaseJobConfig(BaseModel):
    """Base contract for a Job's configuration model.

    A domain config model MUST subclass this so the framework ``Job`` can
    persist, reload, and track the single uploaded input file generically.
    Domains add their own fields on top.
    """

    upload_file_name: Optional[str] = Field(
        None,
        description="Name of the uploaded input file",
        title="Upload file name",
        json_schema_extra={"type": "hidden"},
    )

    job_id: Annotated[
        str,
        Field(
            "poised_python_of_wonder",
            description='Identifier for your submission. Only letters, numbers and "_".',
            title="Job ID",
            json_schema_extra={"type": "text"},
        ),
        AfterValidator(validate_job_id),
    ]

    # Security feature: No model can have an invalid job_id
    model_config = ConfigDict(validate_assignment=True)
