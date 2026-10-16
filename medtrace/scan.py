"""Find trace tags in source and test files.

Two tags, in any comment syntax:

    # @implements SRS-003            (Python, shell, YAML)
    /* @implements SRS-003, SRS-004 */  (C, C++, Java, JS)

    # @verifies SRS-003
    def test_sensor_off_is_reported_as_absent():

`@implements` marks the file (and the definition below it, if any) as
implementing a requirement. `@verifies` must sit directly above a test
function, at most a few lines before its definition (decorators allowed). It
binds to that test, so the test's pass or fail result from a JUnit report can
be attached to the requirement.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

TAG_RE = re.compile(r"@(implements|verifies)\s+([A-Z][A-Z0-9]*-\d+(?:\s*,\s*[A-Z][A-Z0-9]*-\d+)*)")
ID_RE = re.compile(r"[A-Z][A-Z0-9]*-\d+")
DEF_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+(\w+)\s*\("  # Python
    r"|^\s*(?:static\s+|inline\s+|public\s+|void\s+|int\s+)*[\w\*\s]*?\b(\w+)\s*\([^;]*$"  # C-like, no ';'
)
BIND_WINDOW = 6  # lines between a @verifies tag and the test definition it binds to

DEFAULT_INCLUDE = ["**/*.py", "**/*.c", "**/*.h", "**/*.cpp", "**/*.ino", "**/*.ts", "**/*.js", "**/*.java"]
DEFAULT_EXCLUDE = [".git/**", "**/.venv/**", "**/node_modules/**", "**/__pycache__/**", "build/**", "dist/**"]


@dataclass(frozen=True)
class Tag:
    kind: str  # "implements" | "verifies"
    req_id: str
    file: str  # path relative to the repo root, forward slashes
    line: int
    symbol: str | None  # function the tag binds to (the test, for @verifies)


def _matches(rel: str, patterns: list[str]) -> bool:
    """Glob match where "**/" may also match zero directories ("src/**/*.py" matches "src/a.py")."""
    return any(fnmatch.fnmatch(rel, v) for p in patterns for v in {p, p.replace("**/", "")})


def iter_files(root: Path, include=None, exclude=None):
    include = include or DEFAULT_INCLUDE
    exclude = (exclude or []) + DEFAULT_EXCLUDE
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if _matches(rel, exclude) or not _matches(rel, include):
            continue
        yield p, rel


def _next_definition(lines: list[str], start: int) -> str | None:
    for j in range(start, min(start + BIND_WINDOW, len(lines))):
        text = lines[j]
        stripped = text.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", "@")):
            continue  # comments, decorators, blank lines
        m = DEF_RE.match(text)
        if m:
            name = m.group(1) or m.group(2)
            if name not in {"if", "for", "while", "switch", "return", "sizeof"}:
                return name
        return None  # first real code line is not a definition
    return None


def scan(root: Path, include=None, exclude=None) -> tuple[list[Tag], list[str]]:
    """Return tags and problems (unbound @verifies tags)."""
    tags: list[Tag] = []
    problems: list[str] = []
    for path, rel in iter_files(root, include, exclude):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, text in enumerate(lines):
            for m in TAG_RE.finditer(text):
                kind = m.group(1)
                symbol = _next_definition(lines, i + 1)
                if kind == "verifies" and symbol is None:
                    problems.append(f"{rel}:{i + 1}: @verifies is not directly above a test function")
                for rid in ID_RE.findall(m.group(2)):
                    tags.append(Tag(kind, rid, rel, i + 1, symbol))
    return tags, problems
