"""Change impact: which requirements and risks a set of changed files touches.

Uses the tags in the changed files themselves, so the answer follows the code.
Run on a pull request to list what needs re-verification and review.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .scan import Tag


def changed_files(root: Path, base: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=True
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def affected(tags: list[Tag], files: list[str], spec_files: list[str]) -> dict:
    files_set = set(files)
    reqs = sorted({t.req_id for t in tags if t.file in files_set})
    spec_changed = sorted(f for f in files if f in spec_files)
    return {"changed_files": files, "requirements": reqs, "spec_changed": spec_changed}


def markdown(result: dict, spec, trace) -> str:
    lines = ["## Change impact", ""]
    if result["spec_changed"]:
        lines.append(
            f"Requirement or risk files changed: {', '.join(f'`{f}`' for f in result['spec_changed'])}. "
            "Review them as a specification change."
        )
        lines.append("")
    if not result["requirements"]:
        lines.append("No tagged code or tests changed.")
        return "\n".join(lines) + "\n"
    lines += ["| Requirement | Tests to re-run | Risks it controls |", "|---|---|---|"]
    for rid in result["requirements"]:
        req = spec.requirement(rid)
        title = f"{rid}: {req.title}" if req else rid
        tests = ", ".join(sorted({f"`{e.test}`" for e in trace.verified_by.get(rid, [])})) or "none"
        risks = ", ".join(trace.risks_for.get(rid, [])) or ""
        lines.append(f"| {title} | {tests} | {risks} |")
    return "\n".join(lines) + "\n"
