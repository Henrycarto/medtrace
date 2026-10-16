# medtrace

Fails the build when a requirement has no code, no passing test, or a risk has no verified
control.

In medical device software, "we tested it" is not enough. You have to show which requirement
each test verifies, which risk each requirement controls, and that those tests passed on the
code you are releasing. IEC 62304 asks for traceability between software requirements, software
system tests and the risk control measures implemented in software (clauses 5.1.1 and 7.3.3).
Most teams keep that in a spreadsheet, updated by hand before an audit, and it is out of date
the day after.

medtrace keeps it in the repository, next to the code, and checks it on every commit.

```
docs/requirements.yml          SRS-003  Report missing data as absent, with the reason
docs/risks.yml                 HAZ-001  Stored value that does not reflect the patient  → controls SRS-003, ...
pulse_fhir/windows.py          # @implements SRS-003
tests/test_windows.py          # @verifies SRS-003
                               def test_sensor_off_is_reported_as_absent_not_as_a_number(): ...
junit-unit.xml                 test_sensor_off_is_reported_as_absent_not_as_a_number  passed
                                     │
                                     ▼
                     medtrace check --junit junit-*.xml
                     SRS-003 ✅ implemented, verified, passed  → HAZ-001 control verified
```

## What it checks

| Rule | Fails when |
|---|---|
| TR001 | a requirement has no code tagged `@implements` |
| TR002 | a requirement verified by test has no test tagged `@verifies` |
| TR003 | a tag names a requirement that does not exist |
| TR004 | a requirement or risk id is defined twice |
| TR005 | a requirement verified by inspection or analysis has no justification |
| TR006 | a verifying test failed, was skipped, or did not run in this build |
| TR007 | a risk has no control, in software or outside it |
| TR008 | a risk control is not a known requirement |
| TR009 | a risk control requirement is not verified by a passing test |
| TR010 | a risk's residual score is above the acceptability limit |
| TR011 | a `@verifies` tag is not directly above a test function |
| TR012 | a requirement or risk entry is missing a field or out of range |

TR006 and TR009 are the point. A tag only says someone intended a test to cover a requirement.
With `--junit`, medtrace reads the actual test results, so a requirement counts as verified only
if its tests ran and passed in this build. A skipped test or a test that was never collected is
a failure, not a pass. Parametrised tests count as passed only if every case passed.

## Use it

```bash
pip install git+https://github.com/Henrycarto/medtrace@v0.1.0

pytest --junitxml=junit.xml
medtrace check --junit junit.xml --report traceability.md
medtrace impact --base origin/main     # requirements, tests and risks a change touches
```

In GitHub Actions, with results collected from several test jobs:

```yaml
- uses: actions/download-artifact@v4
  with: { pattern: junit-*, merge-multiple: true }
- uses: Henrycarto/medtrace@v0.1.0
  with:
    junit: "junit-*.xml"
```

The matrix is written to the job summary, so every build has its own traceability record.

Tags work in any language with comments: `# @verifies SRS-001` in Python, `/* @verifies FW-001 */`
above a C test function. Any runner that writes JUnit XML works: pytest, Maven Surefire, ctest,
Jest with jest-junit.

## Worked example

[pulse-fhir-gateway](https://github.com/Henrycarto/pulse-fhir-gateway) has 14 software
requirements, 6 hazards and 36 trace tags. Its CI runs unit tests and an integration test against a
real HAPI FHIR server in separate jobs, then runs medtrace on both sets of results.

[`docs/example-pulse-fhir-gateway.md`](docs/example-pulse-fhir-gateway.md) is the matrix from
the unit tests alone. It fails, correctly: two requirements (no duplicates, link to device) are
verified by the integration test, which did not run, so the two hazards they control are not
verified either. With the integration job's results added, the same check passes.

The example also shows a risk with no software control at all (a reading attached to the wrong
patient). It is controlled outside the software, and the matrix says so.

## What it is not

- Not a QMS and not a substitute for one. It checks one piece of evidence: that the trace from
  risk to requirement to code to passing test is complete for this build.
- It does not judge whether a test actually verifies its requirement. That is design review.
- It does not validate itself. If you use it as part of a quality system, validate it for your
  intended use (ISO 13485 clause 4.1.6). `tests/test_rules.py`, one test per rule, is a starting
  point for that, not the validation.
- Risk scoring is a simple severity × probability matrix with one acceptability limit. Real risk
  management files are richer; this covers what the trace needs.

## Author

Samuel Henry Mba. TÜV AUSTRIA certified in Quality and Regulatory Affairs Management
(ISO/IEC 17024).
