"""Markdown traceability matrix: readable in a PR, a GitHub job summary, or printed for an audit."""

from __future__ import annotations

from collections import Counter

from .check import Trace
from .model import Spec

ICON = {
    "passed": "✅ passed",
    "failed": "❌ failed",
    "skipped": "⚠️ skipped",
    "not-run": "⚠️ not run",
    "untested": "❌ no test",
    "tagged": "tagged (no results)",
}


def _cell(items: list[str], limit: int = 4) -> str:
    if not items:
        return "none"
    shown = items[:limit]
    more = f" +{len(items) - limit} more" if len(items) > limit else ""
    return "<br>".join(shown) + more


def markdown(spec: Spec, t: Trace, title: str = "Traceability") -> str:
    out = [f"## {title}", ""]
    errors, warnings = len(t.errors), sum(f.severity == "warning" for f in t.findings)
    statuses = Counter(t.status(r.id) if r.verification == "test" else "n/a" for r in spec.requirements)
    verified = statuses.get("passed", 0) if t.have_results else statuses.get("tagged", 0)
    tested = sum(r.verification == "test" for r in spec.requirements)
    out.append(
        f"**{len(spec.requirements)} requirements, {len(spec.risks)} risks.** "
        f"{verified} of {tested} test-verified requirements {'pass' if t.have_results else 'have tests'}. "
        f"{errors} error(s), {warnings} warning(s)."
    )
    out += [
        "",
        "### Requirements",
        "",
        "| ID | Requirement | Implemented in | Verified by | Result | Risk controls for |",
        "|---|---|---|---|---|---|",
    ]
    for r in spec.requirements:
        impl = sorted({f"`{x.file}`" for x in t.implemented_in.get(r.id, [])})
        tests = [f"`{e.test}`" for e in t.verified_by.get(r.id, [])]
        if r.verification == "test":
            result = ICON[t.status(r.id)]
        else:
            result = f"by {r.verification}"
            tests = [r.justification or "no justification"]
        risks = ", ".join(t.risks_for.get(r.id, [])) or ""
        out.append(f"| {r.id} | {r.title} | {_cell(impl)} | {_cell(tests)} | {result} | {risks} |")

    if spec.risks:
        out += [
            "",
            "### Risks",
            "",
            f"Score = severity × probability (1 to 5 each). Acceptable after controls: {spec.max_risk_score} or less.",
            "",
            "| ID | Hazard → situation → harm | Before | Controls | After |",
            "|---|---|---|---|---|",
        ]
        for k in spec.risks:
            ctrls = [f"{c} ({ICON.get(t.status(c), t.status(c))})" for c in k.controls]
            ctrls += [f"outside software: {e}" for e in k.external_controls]
            after = f"{k.residual_score}" + (" ❌" if k.residual_score > spec.max_risk_score else "")
            out.append(f"| {k.id} | {k.hazard} → {k.situation} → {k.harm} | {k.initial_score} | {_cell(ctrls, 6)} | {after} |")

    if t.findings:
        out += ["", "### Findings", "", "| Rule | Severity | Where | What |", "|---|---|---|---|"]
        for f in sorted(t.findings, key=lambda f: (f.severity != "error", f.rule, f.subject)):
            out.append(f"| {f.rule} | {f.severity} | {f.subject} | {f.message} |")
    out.append("")
    return "\n".join(out)
