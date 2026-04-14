"""Pydantic models for cosmo_template job configuration."""

import logging
import re
from typing import Literal, Optional

from pydantic import AfterValidator, ConfigDict, Field
from pydantic import BaseModel
from typing import Annotated

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


class ProfileConfig(BaseModel):
    """Configuration for CSV statistical profiling."""

    columns: Optional[list[str]] = Field(
        None,
        description="Which columns to analyze (default: all)",
        title="Columns",
        json_schema_extra={"type": "dropdown-checklist"},
    )

    handle_missing: Annotated[
        Literal["drop", "fill_mean", "fill_zero", "keep"],
        Field(
            "drop",
            description="How to handle missing values",
            title="Handle missing values",
            json_schema_extra={"type": "select"},
        ),
    ]

    histogram_bins: Annotated[
        int,
        Field(
            30,
            description="Number of bins for histograms (5–200)",
            title="Histogram bins",
            ge=5,
            le=200,
            json_schema_extra={"type": "integer"},
        ),
    ]

    compute_correlation: Annotated[
        bool,
        Field(
            True,
            description="Compute correlation matrix for numeric columns",
            title="Compute correlation",
            json_schema_extra={"type": "checkbox"},
        ),
    ]

    top_n_categories: Annotated[
        int,
        Field(
            10,
            description="Number of top values for categorical columns (1–100)",
            title="Top N categories",
            ge=1,
            le=100,
            json_schema_extra={"type": "integer"},
        ),
    ]

    trigger_error: Annotated[
        bool,
        Field(
            False,
            description="Deliberately trigger a division by zero error (for testing)",
            title="Trigger error",
            json_schema_extra={"type": "checkbox"},
        ),
    ]

    upload_file_name: Optional[str] = Field(
        None,
        description="Name of the uploaded CSV file",
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
