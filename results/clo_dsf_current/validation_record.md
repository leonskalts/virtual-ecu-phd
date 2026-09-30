# Validation record

Mandatory benign gate failed;480 fault-validation runs not executed.

{
  "head": "1bc6b12d970acc702dea62ad2507f5709a5254cc",
  "planned": 2400,
  "executed": 1920,
  "historical_train_cal_sensor_replays": 10,
  "gate": {
    "runs": 120,
    "A2_alarms": 1,
    "A2_wrong_samples": 1,
    "cold_regressions": 1,
    "passed": false,
    "methods": {
      "A0": {
        "alarms": 0,
        "wrong_samples": 0
      },
      "A1": {
        "alarms": 0,
        "wrong_samples": 0
      },
      "A2": {
        "alarms": 1,
        "wrong_samples": 1
      }
    }
  },
  "protected_unchanged": 21255,
  "archived_previous_files": 7,
  "focused_unit": "PASS",
  "build": "PASS",
  "python_compile": "PASS",
  "full_regression": "NOT RUN: not retained; STOP",
  "retained": "CURRENT",
  "sensor_c_sha256": "b4cd951328299da10fa5b4c0a504e79f9cf8a252b861304e38e77546be4e7be9",
  "gui_sha256": "3fdf2d807ea8661def7e447ff32be0ccf46d70e160e28390bff81aeffbab957a"
}
