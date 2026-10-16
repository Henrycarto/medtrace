"""Read test results from JUnit XML (pytest --junitxml, Maven Surefire, ctest, Jest junit, ...).

A tagged test counts as passed only if every JUnit case for it passed.
Parametrised tests (`test_x[a]`, `test_x[b]`) are grouped under `test_x`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ORDER = {"failed": 3, "skipped": 2, "passed": 1}


@dataclass(frozen=True)
class Result:
    status: str  # passed | failed | skipped
    cases: int


def _status(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def load(paths: list[Path]) -> dict[tuple[str, str], Result]:
    """Map (file stem, test name) to the worst result across its cases."""
    worst: dict[tuple[str, str], str] = {}
    count: dict[tuple[str, str], int] = defaultdict(int)
    for path in paths:
        for case in ET.parse(path).getroot().iter("testcase"):
            name = case.get("name", "").split("[", 1)[0]
            classname = case.get("classname", "")
            file_attr = case.get("file", "")
            stem = Path(file_attr).stem if file_attr else classname.split(".")[-1]
            # pytest puts tests inside classes as "module.Class"; use the module part too
            keys = {(stem, name)}
            parts = classname.split(".")
            if len(parts) >= 2:
                keys.add((parts[-2], name))
            st = _status(case)
            for key in keys:
                count[key] += 1
                prev = worst.get(key)
                worst[key] = st if prev is None else max(prev, st, key=ORDER.get)
    return {k: Result(v, count[k]) for k, v in worst.items()}


def lookup(results: dict[tuple[str, str], Result], file: str, test: str) -> Result | None:
    return results.get((Path(file).stem, test))
