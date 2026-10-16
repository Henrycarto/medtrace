import subprocess
import textwrap
from pathlib import Path

import pytest

REQS = """
requirements:
  - id: SRS-001
    title: Parse input
  - id: SRS-002
    title: Store once
  - id: SRS-003
    title: Manual check of the label
    verification: inspection
    justification: Label text reviewed against the IFU at release
"""
RISKS = """
acceptability: {max_score: 6}
risks:
  - id: HAZ-001
    hazard: Wrong value
    situation: Bad input stored
    harm: Late treatment
    severity: 4
    probability: 3
    controls: [SRS-001]
    residual_probability: 1
"""
CODE = """
# @implements SRS-001
def parse(x):
    return x

# @implements SRS-002, SRS-003
def store(x):
    return x
"""
TESTS = """
import pytest

# @verifies SRS-001
def test_parse():
    assert True

@pytest.mark.slow
# @verifies SRS-002
def test_store():
    assert True
"""


def write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip())
    return root


@pytest.fixture
def repo(tmp_path):
    """A small, fully traced project. Tests change one thing and expect one finding."""
    return write(tmp_path, {"requirements.yml": REQS, "risks.yml": RISKS, "src/app.py": CODE, "tests/test_app.py": TESTS})


def junit(path: Path, cases: dict[str, str]) -> Path:
    """cases: {"test_app::test_parse": "passed" | "failed" | "skipped"}"""
    body = []
    for key, status in cases.items():
        mod, name = key.split("::")
        inner = {"failed": "<failure message='x'/>", "skipped": "<skipped/>", "passed": ""}[status]
        body.append(f'<testcase classname="tests.{mod}" name="{name}">{inner}</testcase>')
    path.write_text(f'<testsuites><testsuite name="pytest">{"".join(body)}</testsuite></testsuites>')
    return path


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout
