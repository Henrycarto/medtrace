## Traceability

**14 requirements, 6 risks.** 12 of 14 test-verified requirements pass. 4 error(s), 0 warning(s).

### Requirements

| ID | Requirement | Implemented in | Verified by | Result | Risk controls for |
|---|---|---|---|---|---|
| SRS-001 | Parse the firmware serial line and drop anything malformed | `pulse_fhir/serial_format.py` | `test_parses_a_firmware_line`<br>`test_rejects_what_the_firmware_never_sends` | ✅ passed |  |
| SRS-002 | One heart rate value per fixed window, timed by sample count | `pulse_fhir/windows.py` | `test_rest_recording_gives_six_steady_values`<br>`test_exercise_step_shows_up_in_the_right_window` | ✅ passed | HAZ-003 |
| SRS-003 | Report a window as absent, with the reason, when the sensor gave too little valid data | `pulse_fhir/fhir.py`<br>`pulse_fhir/windows.py` | `test_sensor_off_window_carries_a_reason`<br>`test_sensor_off_is_reported_as_absent_not_as_a_number` | ✅ passed | HAZ-001, HAZ-004 |
| SRS-004 | Treat a physiologically implausible rate as absent | `pulse_fhir/windows.py` | `test_implausible_median_is_absent` | ✅ passed | HAZ-001 |
| SRS-005 | Use the median so short artefacts do not move the value | `pulse_fhir/windows.py` | `test_median_ignores_the_spike_when_the_sensor_reacquires` | ✅ passed | HAZ-001 |
| SRS-006 | Refuse a start time without a time zone | `pulse_fhir/windows.py` | `test_naive_start_time_is_refused` | ✅ passed | HAZ-003 |
| SRS-007 | Do not report a partial window | `pulse_fhir/windows.py` | `test_trailing_partial_window_is_dropped` | ✅ passed | HAZ-001 |
| SRS-008 | Code each value as a FHIR R4 heart rate vital sign | `pulse_fhir/fhir.py` | `test_bundle_and_every_resource_parse_as_fhir`<br>`test_heart_rate_profile_fixed_values`<br>`test_sensor_off_window_carries_a_reason` | ✅ passed | HAZ-006 |
| SRS-009 | Store each window exactly once, however often it is sent | `pulse_fhir/fhir.py` | `test_identifiers_are_stable_across_rebuilds_and_unique_per_device`<br>`test_every_create_is_conditional_and_references_resolve_in_the_bundle`<br>`test_replaying_twice_stores_each_window_exactly_once` | ⚠️ not run | HAZ-002 |
| SRS-010 | Link every value to the device that measured it | `pulse_fhir/fhir.py` | `test_every_create_is_conditional_and_references_resolve_in_the_bundle`<br>`test_replaying_twice_stores_each_window_exactly_once` | ⚠️ not run | HAZ-006 |
| SRS-011 | Retry temporary server and network failures | `pulse_fhir/delivery.py` | `test_retries_transient_failures_then_succeeds`<br>`test_honours_retry_after`<br>`test_gives_up_after_the_attempt_budget` | ✅ passed | HAZ-004 |
| SRS-012 | Keep undelivered data across outages and restarts, and deliver it in order | `pulse_fhir/delivery.py` | `test_outbox_keeps_everything_while_the_server_is_down`<br>`test_outbox_sends_in_order_once_the_server_is_back`<br>`test_outbox_survives_a_restart` | ✅ passed | HAZ-004 |
| SRS-013 | Set aside bundles the server rejects, without blocking the rest | `pulse_fhir/delivery.py` | `test_does_not_retry_a_bundle_the_server_rejected`<br>`test_a_rejected_bundle_goes_to_dead_letter_and_does_not_block_the_queue` | ✅ passed | HAZ-004 |
| SRS-014 | Authenticate with a bearer token when one is configured | `pulse_fhir/cli.py`<br>`pulse_fhir/delivery.py` | `test_posts_fhir_json_with_bearer_token` | ✅ passed |  |

### Risks

Score = severity × probability (1 to 5 each). Acceptable after controls: 6 or less.

| ID | Hazard → situation → harm | Before | Controls | After |
|---|---|---|---|---|
| HAZ-001 | Stored heart rate that does not reflect the patient → Sensor off or artefact during a window, and a number is stored anyway → Clinician trusts a normal-looking value and recognises deterioration late | 12 | SRS-003 (✅ passed)<br>SRS-004 (✅ passed)<br>SRS-005 (✅ passed)<br>SRS-007 (✅ passed) | 4 |
| HAZ-002 | The same reading stored more than once → A retry after a timeout creates a second copy → Distorted trend or counts lead to a wrong judgement of stability | 8 | SRS-009 (⚠️ not run) | 2 |
| HAZ-003 | Reading stored with the wrong time → Time taken from bursty USB arrival, or a start time without a time zone → A change is attributed to the wrong moment, for example before or after a medication | 9 | SRS-002 (✅ passed)<br>SRS-006 (✅ passed) | 3 |
| HAZ-004 | Readings lost without trace → Server or network unavailable while the device records → A gap is read as "nothing happened" | 12 | SRS-011 (✅ passed)<br>SRS-012 (✅ passed)<br>SRS-013 (✅ passed)<br>SRS-003 (✅ passed) | 3 |
| HAZ-005 | Reading attached to the wrong patient → The wrong patient identifier is given when the device is started → Decision made on another patient's data | 8 | outside software: Device-to-patient assignment is done in the clinical workflow and checked at the bedside; the gateway only passes the identifier it is given | 4 |
| HAZ-006 | Reading with unknown origin → Values from several devices cannot be told apart → A faulty device's values cannot be found and excluded | 6 | SRS-010 (⚠️ not run)<br>SRS-008 (✅ passed) | 3 |

### Findings

| Rule | Severity | Where | What |
|---|---|---|---|
| TR006 | error | SRS-009 | tests/test_integration.py::test_replaying_twice_stores_each_window_exactly_once did not run |
| TR006 | error | SRS-010 | tests/test_integration.py::test_replaying_twice_stores_each_window_exactly_once did not run |
| TR009 | error | HAZ-002 | control SRS-009 is not verified by a passing test (not-run) |
| TR009 | error | HAZ-006 | control SRS-010 is not verified by a passing test (not-run) |
