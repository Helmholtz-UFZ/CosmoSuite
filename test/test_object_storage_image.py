"""The S3 server image is written in three places here; they must name the same one.

CI takes it from ``ci/object-storage.gitlab-ci.yml``, local runs from the example's
compose file, and apps copy their compose block from the convention doc. If only
one of them moves, CI and local runs test against different servers, and a
consumer copies a stale block — none of which fails on its own.

Parsed with regexes, like ``test_version.py``: pyyaml is not a dependency, and
the markdown copy is not YAML anyway.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

CI_TEMPLATE = REPO_ROOT / "ci" / "object-storage.gitlab-ci.yml"
COMPOSE_FILES = (
    REPO_ROOT / "examples" / "csv_profiler" / "docker-compose.yml",
    REPO_ROOT / "docs" / "conventions" / "object_storage.md",
)

CI_IMAGE_PATTERN = re.compile(r'^\s*- name: "([^"]+)"\s*$', re.M)
COMPOSE_IMAGE_PATTERN = re.compile(r"^  object-storage:\n    image: (\S+)\s*$", re.M)


def test_ci_template_has_exactly_one_service():
    assert len(CI_IMAGE_PATTERN.findall(CI_TEMPLATE.read_text())) == 1


def test_compose_blocks_use_the_ci_image():
    (ci_image,) = CI_IMAGE_PATTERN.findall(CI_TEMPLATE.read_text())

    for path in COMPOSE_FILES:
        images = COMPOSE_IMAGE_PATTERN.findall(path.read_text())
        assert images == [ci_image], f"{path.relative_to(REPO_ROOT)}: {images}"
