"""Test the framework's object storage manager against MinIO."""

import os
import shutil
import urllib.request
from datetime import timedelta

from cosmo_suite.config import JOB_WORK_DIR_TEMPLATE
from cosmo_suite.object_storage_manager import (
    delete_directory_from_storage,
    get_presigned_download_url,
    save_files,
)

JOB_ID = "test_presigned_download_url"
FILE_NAME = "result.csv"
CONTENT = "col_a,col_b\n1,2\n"


def test_presigned_url_downloads_without_credentials():
    """A presigned URL serves the object to a client that has no credentials.

    This is the off-network download path (cosmonaut's QR code): the URL must
    carry its own auth, so the request below deliberately passes none.
    """
    work_dir = JOB_WORK_DIR_TEMPLATE.format(job_id=JOB_ID)
    os.makedirs(work_dir, exist_ok=True)
    with open(os.path.join(work_dir, FILE_NAME), "w", encoding="UTF-8") as f_handle:
        f_handle.write(CONTENT)

    save_files(JOB_ID)

    try:
        url = get_presigned_download_url(
            f"{JOB_ID}/{FILE_NAME}",
            timedelta(minutes=5),
        )
        with urllib.request.urlopen(url) as response:
            downloaded = response.read().decode("UTF-8")
    finally:
        delete_directory_from_storage(JOB_ID)
        shutil.rmtree(work_dir, ignore_errors=True)

    # A plain object URL would also download here (the test bucket is reachable),
    # so assert the signature is actually part of the URL.
    assert "X-Amz-Signature=" in url
    assert downloaded == CONTENT
