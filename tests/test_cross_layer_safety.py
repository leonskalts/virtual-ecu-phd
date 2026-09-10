"""Behavioral integration checks: make && python3 -m unittest discover -s tests -v."""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from virtual_ecu.cross_layer_safety import STAGES, fault_options, read_rows, summarize_rows


class CrossLayerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="vecu_cross_layer_")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)

    def run_case(self, name, options=(), campaign=("baseline",)):
        path = self.path / (name + ".csv")
        subprocess.run([str(ROOT / "virtual_ecu"), str(path), *campaign, *options],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        return read_rows(path)

    def test_baseline_monitor_is_passive_and_empty_stages_are_unavailable(self):
        old = self.run_case("plain")
        new = self.run_case("monitored", ["--cross-layer-monitor", "on"])
        legacy_columns = list(old[0])[:list(old[0]).index("cross_layer_fault_enabled")]
        self.assertEqual([{k: r[k] for k in legacy_columns} for r in old],
                         [{k: r[k] for k in legacy_columns} for r in new])
        self.assertTrue(all(r["cross_layer_fault_enabled"] == "0" for r in new))
        self.assertTrue(all(r["plant_coolant_deviation_c"] == "0.000000000" for r in new))
        self.assertTrue(all(new[-1][stage] == "" for stage in STAGES))
        self.assertIsNone(summarize_rows(new)["safe_state_reached"])

    def test_actual_integer_flip_and_restore_for_each_supported_bit(self):
        for bit in range(6):
            with self.subTest(bit=bit):
                rows = self.run_case(f"memory{bit}", fault_options("bit_flip", duration_ms=300, bit_index=bit))
                at = {int(r["time_ms"]): r for r in rows}
                self.assertEqual(at[44900]["memory_original_value"], "")
                for time in (45000, 45100, 45200):
                    self.assertEqual(at[time]["fault_injection_active"], "1")
                    self.assertEqual(int(at[time]["memory_original_value"]), 92)
                    self.assertEqual(int(at[time]["memory_corrupted_value"]), 92 ^ (1 << bit))
                    self.assertEqual(float(at[time]["active_control_target_c"]), 92 ^ (1 << bit))
                self.assertEqual(at[45300]["fault_injection_active"], "0")
                self.assertEqual(float(at[45300]["active_control_target_c"]), 92)
                self.assertEqual(at[45000]["coolant_temp_true_c"], at[45000]["coolant_temp_meas_c"])
                for key in ("fault_injection_ms", "propagation_internal_ms", "propagation_control_ms"):
                    self.assertEqual(rows[-1][key], "45000")

    def test_skipped_execution_and_recovery_do_not_mutate_plant(self):
        baseline = self.run_case("clean", ["--cross-layer-monitor", "on"])
        rows = self.run_case("deadline", fault_options("deadline_miss"))
        at = {int(r["time_ms"]): r for r in rows}
        clean = {int(r["time_ms"]): r for r in baseline}
        skipped = [r for r in rows if r["control_task_execution_skipped"] == "1"]
        self.assertEqual([r["time_ms"] for r in skipped], ["45000"])
        self.assertEqual(skipped[0]["control_task_expected_execution_ms"], "45000")
        self.assertEqual(skipped[0]["control_task_actual_execution_ms"], "")
        self.assertEqual(skipped[0]["control_task_delay_ms"], "")
        self.assertEqual(skipped[0]["control_task_last_execution_ms"], "44900")
        self.assertEqual(at[45100]["control_task_actual_execution_ms"], "45100")
        self.assertEqual(at[45100]["control_task_recovery"], "1")
        self.assertEqual(sum(int(r["control_task_recovery"]) for r in rows), 1)
        for key in ("pump_command", "fan_command", "active_control_target_c"):
            self.assertEqual(at[45000][key], at[44900][key])
        self.assertEqual(at[45000]["coolant_temp_true_c"], clean[45000]["coolant_temp_true_c"])
        self.assertTrue(all(r["memory_original_value"] == "" for r in rows))
        self.assertEqual(rows[-1]["propagation_plant_ms"], "")
        self.assertEqual(rows[-1]["cross_layer_detection_latency_ms"], "")

    def test_causal_propagation_and_metrics_with_safety_response(self):
        rows = self.run_case("strong", [*fault_options("bit_flip"), "--detector",
                                        "hybrid_adaptive_kalman", "--detector-action", "limp_home"])
        last = rows[-1]
        times = [int(last[k]) for k in STAGES[:6]]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[:5], [45000] * 5)
        self.assertEqual(times[-1], 45100)
        self.assertEqual(last["cross_layer_detection_latency_ms"], "0")
        self.assertEqual(last["detection_to_safety_response_latency_ms"], "0")
        self.assertEqual(last["detected_before_plant_manifestation"], "1")
        self.assertEqual(last["safe_state_reached"], "1")
        self.assertEqual(last["propagation_depth"], "5")
        self.assertEqual(last["containment_success"], "")
        self.assertEqual(last["unsafe_exposure_time_ms"], "0")
        self.assertEqual(last["silent_corruption"], "0")

    def test_seed_and_fault_id_cannot_change_detector_output(self):
        rows = self.run_case("first", [*fault_options("bit_flip", seed=42),
                                      "--detector", "hybrid_adaptive_kalman"])
        self.run_case("repeat", [*fault_options("bit_flip", seed=42),
                                 "--detector", "hybrid_adaptive_kalman"])
        self.assertEqual((self.path / "first.csv").read_bytes(), (self.path / "repeat.csv").read_bytes())
        other = self.run_case("metadata", [*fault_options("bit_flip", seed=99, fault_id=987),
                                          "--detector", "hybrid_adaptive_kalman"])
        keys = [k for k in rows[0] if k.startswith("runtime_detection_")]
        self.assertEqual([{k: r[k] for k in keys} for r in rows],
                         [{k: r[k] for k in keys} for r in other])
        for source in ("src/detection_algorithm.c", "src/diagnostics.c", "src/safety_monitor.c",
                       "python/virtual_ecu/detection_algorithms.py"):
            text = (ROOT / source).read_text()
            self.assertNotIn("cross_layer", text)
            self.assertNotIn("propagation", text)

    def test_old_csv_missing_fields_remain_unavailable(self):
        rows = self.run_case("legacy")
        columns = list(rows[0])[:list(rows[0]).index("cross_layer_fault_enabled")]
        path = self.path / "old_schema.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        report = summarize_rows(read_rows(path))
        self.assertFalse(report["telemetry_available"])
        for key in (*STAGES, "injected", "detected", "plant_manifestation", "propagation_depth"):
            self.assertIsNone(report[key])

    def test_invalid_configurations_fail(self):
        for options in (
            ["--cross-layer-fault", "unknown_model"],
            ["--cross-layer-fault", "bit_flip", "--bit-index", "6"],
            ["--cross-layer-fault", "bit_flip", "--fault-start-ms", "45001"],
            ["--cross-layer-fault", "bit_flip", "--fault-duration-ms", "0"],
            ["--cross-layer-fault", "bit_flip", "--fault-behavior", "randomized"],
            ["--cross-layer-fault", "bit_flip", "--fault-layer", "timing"],
            ["--cross-layer-fault", "bit_flip", "--fault-target", "fan"],
            ["--cross-layer-fault", "bit_flip", "--fault-strat-ms", "45000"],
            ["--cross-layer-fault", "deadline_miss", "--fault-duration-ms", "200"],
            ["--cross-layer-fault", "deadline_miss", "--bit-index", "3"],
            ["--cross-layer-fault", "bit_flip", "--fault-start-ms", "120000"],
            ["--cross-layer-fault", "bit_flip", "--fault-duration-ms", "4294967200"],
            ["--fault-start-ms", "45000"], ["--seed", "-1"], ["--seed", "4294967296"],
            ["--seed", "junk"], ["--seed"],
        ):
            with self.subTest(options=options):
                result = subprocess.run([str(ROOT / "virtual_ecu"), str(self.path / "bad.csv"),
                                         "baseline", *options], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.path / "bad.csv").exists())


if __name__ == "__main__":
    unittest.main()
