from conftest import junit, write

from medtrace.check import build
from medtrace.model import load
from medtrace.scan import scan

ALL_PASS = {"test_app::test_parse": "passed", "test_app::test_store": "passed"}


def run(root, results=None):
    spec = load(root / "requirements.yml", root / "risks.yml")
    tags, problems = scan(root, exclude=["requirements.yml", "risks.yml"])
    return build(spec, tags, problems, results)


def rules(trace, severity="error"):
    return sorted({f.rule for f in trace.findings if f.severity == severity})


def results_for(tmp_path, cases):
    from medtrace import junit as j

    return j.load([junit(tmp_path / "r.xml", cases)])


def test_a_fully_traced_project_is_clean(repo):
    t = run(repo, results_for(repo, ALL_PASS))
    assert t.findings == []
    assert t.status("SRS-001") == "passed"


def test_without_results_only_a_warning_is_raised(repo):
    t = run(repo)
    assert rules(t) == [] and rules(t, "warning") == ["TR006"]
    assert t.status("SRS-001") == "tagged"


def test_TR001_requirement_with_no_code(repo):
    (repo / "src/app.py").write_text("# @implements SRS-002, SRS-003\ndef store(x):\n    return x\n")
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR001"]


def test_TR002_and_TR009_test_removed_from_a_risk_control(repo):
    text = (repo / "tests/test_app.py").read_text().replace("# @verifies SRS-001\n", "")
    (repo / "tests/test_app.py").write_text(text)
    t = run(repo, results_for(repo, ALL_PASS))
    assert rules(t) == ["TR002", "TR009"]


def test_TR003_tag_for_an_unknown_requirement(repo):
    (repo / "src/extra.py").write_text("# @implements SRS-099\ndef f():\n    pass\n")
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR003"]


def test_TR004_duplicate_id(repo):
    text = (repo / "requirements.yml").read_text() + "  - id: SRS-001\n    title: again\n"
    (repo / "requirements.yml").write_text(text)
    assert "TR004" in rules(run(repo, results_for(repo, ALL_PASS)))


def test_TR005_inspection_without_justification(repo):
    text = (
        (repo / "requirements.yml").read_text().replace("    justification: Label text reviewed against the IFU at release\n", "")
    )
    (repo / "requirements.yml").write_text(text)
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR005"]


def test_TR006_failed_skipped_and_missing_tests(repo):
    for status in ("failed", "skipped"):
        t = run(repo, results_for(repo, {**ALL_PASS, "test_app::test_store": status}))
        assert rules(t) == ["TR006"], status
        assert t.status("SRS-002") == status
    t = run(repo, results_for(repo, {"test_app::test_parse": "passed"}))
    assert rules(t) == ["TR006"] and t.status("SRS-002") == "not-run"


def test_a_parametrised_test_fails_if_any_case_fails(repo):
    cases = {"test_app::test_parse[a]": "passed", "test_app::test_parse[b]": "failed", "test_app::test_store": "passed"}
    t = run(repo, results_for(repo, cases))
    assert t.status("SRS-001") == "failed"
    assert set(rules(t)) == {"TR006", "TR009"}


def test_TR007_risk_without_any_control(repo):
    text = (repo / "risks.yml").read_text().replace("controls: [SRS-001]", "controls: []")
    (repo / "risks.yml").write_text(text)
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR007"]


def test_an_external_control_counts_as_a_control(repo):
    text = (
        (repo / "risks.yml")
        .read_text()
        .replace("controls: [SRS-001]", "controls: []\n    external_controls: [Checked at the bedside]")
    )
    (repo / "risks.yml").write_text(text)
    assert rules(run(repo, results_for(repo, ALL_PASS))) == []


def test_TR008_control_that_is_not_a_requirement(repo):
    text = (repo / "risks.yml").read_text().replace("controls: [SRS-001]", "controls: [SRS-001, SRS-404]")
    (repo / "risks.yml").write_text(text)
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR008"]


def test_TR010_residual_risk_too_high(repo):
    text = (repo / "risks.yml").read_text().replace("residual_probability: 1", "residual_probability: 2")
    (repo / "risks.yml").write_text(text)
    assert rules(run(repo, results_for(repo, ALL_PASS))) == ["TR010"]


def test_TR011_verifies_tag_not_above_a_test(repo):
    (repo / "tests/test_more.py").write_text("# @verifies SRS-001\nx = 1\n\ndef test_other():\n    pass\n")
    assert "TR011" in rules(run(repo, results_for(repo, ALL_PASS)))


def test_TR012_bad_spec_values(repo):
    text = (repo / "risks.yml").read_text().replace("severity: 4", "severity: 9")
    (repo / "risks.yml").write_text(text)
    assert "TR012" in rules(run(repo, results_for(repo, ALL_PASS)))


def test_c_tests_and_block_comments_are_traced(tmp_path):
    write(
        tmp_path,
        {
            "requirements.yml": "requirements:\n  - id: FW-001\n    title: Detect beats\n",
            "src/detect.c": "/* @implements FW-001 */\nint detect(int x) {\n  return x;\n}\n",
            "test/test_detect.c": "/* @verifies FW-001 */\nstatic void test_detect_nominal(void) {\n  assert(1);\n}\n",
        },
    )
    spec = load(tmp_path / "requirements.yml", None)
    tags, problems = scan(tmp_path, exclude=["requirements.yml"])
    t = build(spec, tags, problems, results_for(tmp_path, {"test_detect::test_detect_nominal": "passed"}))
    assert problems == [] and t.findings == []
    assert t.verified_by["FW-001"][0].test == "test_detect_nominal"
