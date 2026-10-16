from conftest import git, junit

from medtrace.cli import main


def test_check_exit_codes_and_report(repo, tmp_path, capsys):
    ok = junit(tmp_path / "ok.xml", {"test_app::test_parse": "passed", "test_app::test_store": "passed"})
    bad = junit(tmp_path / "bad.xml", {"test_app::test_parse": "failed", "test_app::test_store": "passed"})
    out = tmp_path / "trace.md"
    assert main(["--root", str(repo), "check", "--junit", str(ok), "--report", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "| SRS-001 | Parse input | `src/app.py` | `test_parse` | ✅ passed | HAZ-001 |" in md
    assert "by inspection" in md
    assert main(["--root", str(repo), "check", "--junit", str(bad)]) == 1
    assert "TR009 HAZ-001" in capsys.readouterr().out


def test_strict_turns_the_missing_results_warning_into_a_failure(repo):
    assert main(["--root", str(repo), "check"]) == 0
    assert main(["--root", str(repo), "check", "--strict"]) == 1


def test_github_job_summary_is_written(repo, tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    main(["--root", str(repo), "check"])
    assert summary.read_text().startswith("## Traceability")


def test_impact_lists_requirements_tests_and_risks_touched_by_a_change(repo, capsys):
    git(repo, "init", "-q", "-b", "main")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    git(repo, "checkout", "-qb", "change")
    app = repo / "src/app.py"
    app.write_text(app.read_text() + "\n# tweak\n")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "change")
    assert main(["--root", str(repo), "impact", "--base", "main"]) == 0
    out = capsys.readouterr().out
    assert "SRS-001: Parse input | `test_parse` | HAZ-001" in out
    assert "SRS-002: Store once" in out
