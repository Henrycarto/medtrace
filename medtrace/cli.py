"""medtrace: check that every requirement is implemented, tested, and passing, and every risk is controlled.

  medtrace check                         # tags only
  medtrace check --junit report.xml      # tags plus test outcomes
  medtrace check --junit report.xml --report trace.md
  medtrace impact --base origin/main     # what a change touches

Configuration (optional) in medtrace.yml at the repo root:
  requirements: docs/requirements.yml
  risks: docs/risks.yml
  include: ["pulse_fhir/**/*.py", "tests/**/*.py"]
  exclude: []
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from . import check as check_mod
from . import impact as impact_mod
from . import junit, model, report, scan


def _config(root: Path) -> dict:
    p = root / "medtrace.yml"
    cfg = yaml.safe_load(p.read_text()) if p.exists() else {}
    return {
        "requirements": cfg.get("requirements", "requirements.yml"),
        "risks": cfg.get("risks", "risks.yml"),
        "include": cfg.get("include"),
        "exclude": cfg.get("exclude", []),
    }


def _load(root: Path, junit_paths: list[str] | None):
    cfg = _config(root)
    req_path = root / cfg["requirements"]
    if not req_path.exists():
        sys.exit(f"medtrace: {req_path} not found")
    spec = model.load(req_path, root / cfg["risks"])
    tags, problems = scan.scan(root, cfg["include"], cfg["exclude"] + [cfg["requirements"], cfg["risks"]])
    results = junit.load([Path(p) for p in junit_paths]) if junit_paths else None
    return cfg, spec, tags, check_mod.build(spec, tags, problems, results)


def _summary(md: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(md + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="medtrace", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="repository root (default: current directory)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--junit", action="append", help="JUnit XML with test results; repeatable")
    c.add_argument("--report", help="write the Markdown matrix to this file")
    c.add_argument("--strict", action="store_true", help="treat warnings as errors")
    i = sub.add_parser("impact")
    i.add_argument("--base", required=True, help="git ref to compare against, e.g. origin/main")
    a = p.parse_args(argv)
    root = Path(a.root).resolve()

    if a.cmd == "check":
        _, spec, _, trace = _load(root, a.junit)
        md = report.markdown(spec, trace)
        if a.report:
            Path(a.report).write_text(md, encoding="utf-8")
        _summary(md)
        for f in sorted(trace.findings, key=lambda f: (f.severity != "error", f.rule)):
            print(f"{f.severity.upper():7} {f.rule} {f.subject}: {f.message}")
        n_err = len(trace.errors)
        n_warn = len(trace.findings) - n_err
        print(f"medtrace: {len(spec.requirements)} requirements, {len(spec.risks)} risks, {n_err} error(s), {n_warn} warning(s)")
        return 1 if n_err or (a.strict and n_warn) else 0

    cfg, spec, tags, trace = _load(root, None)
    files = impact_mod.changed_files(root, a.base)
    res = impact_mod.affected(tags, files, [cfg["requirements"], cfg["risks"]])
    md = impact_mod.markdown(res, spec, trace)
    _summary(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
