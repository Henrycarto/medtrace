"""Traceability rules. Each finding has a stable rule id so CI output can be searched.

Errors fail the build; warnings do not (unless --strict).

TR001  requirement has no @implements anywhere
TR002  requirement verified by test has no @verifies test
TR003  tag points at an id that is not in requirements.yml
TR004  requirement or risk id defined twice
TR005  requirement not verified by test has no justification
TR006  a verifying test failed, was skipped, or did not run (needs JUnit results)
TR007  risk has no control at all, in software or outside it
TR008  risk control is not a known requirement
TR009  risk control requirement is not verified by a passing test (needs JUnit results)
TR010  residual risk above the acceptability limit
TR011  @verifies tag not bound to a test function
TR012  spec file problem (missing field, value out of range)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .junit import Result, lookup
from .model import Spec
from .scan import Tag


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # error | warning
    subject: str  # requirement / risk id, or file:line
    message: str


@dataclass
class TestEvidence:
    file: str
    test: str
    result: Result | None  # None when no JUnit results were given or the test did not run


@dataclass
class Trace:
    implemented_in: dict[str, list[Tag]] = field(default_factory=lambda: defaultdict(list))
    verified_by: dict[str, list[TestEvidence]] = field(default_factory=lambda: defaultdict(list))
    risks_for: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    findings: list[Finding] = field(default_factory=list)
    have_results: bool = False

    def status(self, rid: str) -> str:
        """passed | failed | untested | not-run | n/a (verified by inspection or analysis)."""
        ev = self.verified_by.get(rid, [])
        if not ev:
            return "untested"
        if not self.have_results:
            return "tagged"
        states = {e.result.status if e.result else "not-run" for e in ev}
        if "failed" in states:
            return "failed"
        if states == {"passed"}:
            return "passed"
        return "not-run" if "not-run" in states else "skipped"

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]


def build(spec: Spec, tags: list[Tag], scan_problems: list[str], results: dict | None = None) -> Trace:
    t = Trace(have_results=results is not None)
    add = t.findings.append
    known = {r.id for r in spec.requirements}

    for p in spec.problems:
        add(Finding("TR012", "error", "spec", p))
    for p in scan_problems:
        add(Finding("TR011", "error", p.split(": ", 1)[0], p.split(": ", 1)[1]))
    for rid, n in Counter([r.id for r in spec.requirements] + [r.id for r in spec.risks]).items():
        if n > 1:
            add(Finding("TR004", "error", rid, f"defined {n} times"))

    for tag in tags:
        if tag.req_id not in known:
            add(Finding("TR003", "error", f"{tag.file}:{tag.line}", f"@{tag.kind} {tag.req_id}: no such requirement"))
            continue
        if tag.kind == "implements":
            t.implemented_in[tag.req_id].append(tag)
        elif tag.symbol:
            res = lookup(results, tag.file, tag.symbol) if results is not None else None
            t.verified_by[tag.req_id].append(TestEvidence(tag.file, tag.symbol, res))

    for risk in spec.risks:
        for c in risk.controls:
            t.risks_for[c].append(risk.id)

    for req in spec.requirements:
        if not t.implemented_in.get(req.id):
            add(Finding("TR001", "error", req.id, "no code is tagged @implements for it"))
        if req.verification == "test":
            if not t.verified_by.get(req.id):
                add(Finding("TR002", "error", req.id, "no test is tagged @verifies for it"))
            elif t.have_results:
                for e in t.verified_by[req.id]:
                    if e.result is None:
                        add(Finding("TR006", "error", req.id, f"{e.file}::{e.test} did not run"))
                    elif e.result.status != "passed":
                        add(Finding("TR006", "error", req.id, f"{e.file}::{e.test} {e.result.status}"))
        elif not req.justification:
            add(Finding("TR005", "error", req.id, f"verified by {req.verification} but no justification given"))

    for risk in spec.risks:
        if not risk.controls and not risk.external_controls:
            add(Finding("TR007", "error", risk.id, "no risk control in software or outside it"))
        for c in risk.controls:
            if c not in known:
                add(Finding("TR008", "error", risk.id, f"control {c} is not a requirement"))
            elif t.have_results and t.status(c) != "passed" and spec.requirement(c).verification == "test":
                add(Finding("TR009", "error", risk.id, f"control {c} is not verified by a passing test ({t.status(c)})"))
        if risk.residual_score > spec.max_risk_score:
            add(
                Finding(
                    "TR010",
                    "error",
                    risk.id,
                    f"residual risk {risk.residual_score} above the acceptable maximum {spec.max_risk_score}",
                )
            )
    if not t.have_results:
        add(
            Finding(
                "TR006", "warning", "results", "no JUnit results given: tags were checked, test outcomes were not (use --junit)"
            )
        )
    return t
