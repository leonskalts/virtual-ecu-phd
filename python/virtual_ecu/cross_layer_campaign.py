"""YAML/JSON-driven cross-layer campaigns and denominator-explicit analysis."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .cross_layer_safety import (
    PROJECT_ROOT, MODEL_TARGETS, METRICS, STAGES, V2_METRICS,
    fault_options, load_summary, write_rows,
)

DEFAULT_CAMPAIGN_DIR = PROJECT_ROOT / "results" / "cross_layer_safety_v2"
DEFAULT_STUDY = PROJECT_ROOT / "studies" / "cross_layer_vts_candidate_v1.yaml"
PARAMETERS = {
    "start_ms", "duration_ms", "bit_index", "stuck_polarity", "communication_delay_ms",
    "drop_count", "drop_every_n_updates", "replay_age_ms", "task_delay_ms",
    "intermittent_on_ms", "intermittent_off_ms", "seed", "behavior", "parameter",
}
RATE_FIELDS = {
    "detection_coverage": "detected", "plant_propagation_rate": "plant_manifestation",
    "hazard_entry_rate": "hazard_entered", "containment_success_rate": "containment_success",
    "ftti_success_rate": "ftti_met", "silent_corruption_rate": "silent_corruption",
    "safe_state_rate": "safe_state_reached",
}


def read_study(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        config = yaml.safe_load(text)
    else:
        config = json.loads(text)
    if config.get("schema_version") != 1:
        raise ValueError("Expected campaign schema_version 1")
    required = {"profiles", "fault_cases", "hazard", "detectors", "seeds", "injection_times_ms"}
    if required - config.keys():
        raise ValueError(f"Missing study fields: {sorted(required - config.keys())}")
    return config


def expand_runs(config: dict) -> list[dict]:
    """Cartesian products are specified entirely by JSON, never by this runner."""
    runs = []
    for profile, detector in itertools.product(config["profiles"], config["detectors"]):
        if config.get("include_baseline", True):
            runs.append({"profile": profile, "detector": detector, "case_id": "baseline",
                         "model": "baseline", "parameters": {"seed": config["seeds"][0]}})
        for case in config["fault_cases"]:
            model = case["model"]
            if model not in MODEL_TARGETS and model not in ("sensor_bias", "pump_degraded", "fan_stuck_off"):
                raise ValueError(f"Unsupported case model {model}")
            grid = {"start_ms": profile.get("injection_times_ms", config["injection_times_ms"]), "seed": config["seeds"],
                    "behavior": [case.get("behavior", "transient")], **case.get("grid", {})}
            fixed = case.get("parameters", {})
            if (set(grid) | set(fixed)) - PARAMETERS:
                raise ValueError(f"Unknown parameters in case {case['id']}")
            if set(grid) & set(fixed):
                raise ValueError(f"Parameters specified both fixed and grid in {case['id']}")
            if any(not isinstance(v, list) or not v for v in grid.values()):
                raise ValueError("Every grid dimension must be a nonempty list")
            if model in MODEL_TARGETS:
                layer, target = MODEL_TARGETS[model]
                if case.get("layer", layer) != layer or case.get("target", target) != target:
                    raise ValueError(f"Inconsistent layer/target in {case['id']}")
            for values in itertools.product(*grid.values()):
                runs.append({"profile": profile, "detector": detector, "case_id": case["id"],
                             "model": model, "parameters": {**fixed, **dict(zip(grid, values))}})
    for i, run in enumerate(runs):
        run["run_id"] = f"run_{i:04d}_{run['profile']['id']}_{run['case_id']}"
    return runs


def command_for_run(run: dict, config: dict, path: Path) -> list[str]:
    profile, params, model = run["profile"], dict(run["parameters"]), run["model"]
    detector = run["detector"]
    command = [str(PROJECT_ROOT / "virtual_ecu"), str(path)]
    if model in MODEL_TARGETS:
        command += ["baseline", *fault_options(model, **params)]
    elif model == "baseline":
        command += ["baseline", "--seed", str(params["seed"])]
    else:
        command += ["custom", model, str(params["start_ms"]), str(params.get("duration_ms", 10000)),
                    params["behavior"], str(params.get("parameter", 0)), "--seed", str(params["seed"])]
    command += ["--cross-layer-monitor", "on", "--hazard-monitor", "on",
                "--simulation-duration-ms", str(profile["duration_ms"]),
                "--detector", detector["algorithm"], "--detector-action", detector["action"]]
    if profile.get("path"):
        command += ["--driving-profile", str(PROJECT_ROOT / profile["path"])]
    hazard_names = {
        "warning_threshold_c": "hazard-warning-c", "critical_threshold_c": "hazard-critical-c",
        "max_critical_exposure_ms": "max-critical-exposure-ms",
        "fault_tolerant_time_interval_ms": "ftti-ms", "recovery_hold_ms": "containment-hold-ms",
    }
    for name, value in config["hazard"].items():
        if name not in hazard_names:
            raise ValueError(f"Unknown hazard setting {name}")
        command += ["--" + hazard_names[name], str(value)]
    return command


def group_statistics(rows: list[dict], group: str = "overall") -> dict:
    injected = [r for r in rows if r.get("injected") == 1]
    result = {"group": group, "run_count": len(rows), "injected_run_count": len(injected),
              "fault_injection_count": sum(r.get("fault_activation_count") or r.get("injected") or 0 for r in rows)}
    for label, key in RATE_FIELDS.items():
        eligible = [r[key] for r in injected if r.get(key) is not None and
                    (key != "hazard_entered" or not r.get("preexisting_hazard"))]
        count = sum(int(value == 1) for value in eligible)
        result.update({label + "_numerator": count, label + "_denominator": len(eligible),
                       label + "_percent": 100 * count / len(eligible) if eligible else None})
    for label, key in (("plant_propagation_latency_ms", "injection_to_plant_latency_ms"),
                       ("detection_latency_ms", "cross_layer_detection_latency_ms"),
                       ("safety_reaction_latency_ms", "detection_to_safety_response_latency_ms")):
        values = [r[key] for r in injected if r.get(key) is not None]
        result[label + "_n"] = len(values)
        result[label + "_mean"] = statistics.mean(values) if values else None
        result[label + "_median"] = statistics.median(values) if values else None
    exposure = [r["critical_exposure_time_ms"] for r in injected if r.get("critical_exposure_time_ms") is not None]
    result["unsafe_exposure_n"] = len(exposure)
    result["unsafe_exposure_mean_ms"] = statistics.mean(exposure) if exposure else None
    result["unsafe_exposure_median_ms"] = statistics.median(exposure) if exposure else None
    result["unsafe_exposure_max_ms"] = max(exposure) if exposure else None
    result["unsafe_exposure_distribution_ms"] = json.dumps(dict(sorted(Counter(exposure).items())))
    result["propagation_depth_distribution"] = json.dumps(dict(sorted(Counter(
        r["propagation_depth"] for r in injected if r.get("propagation_depth") is not None).items())))
    return result


def grouped(rows: list[dict], key: str) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "baseline")].append(row)
    return [group_statistics(value, name) for name, value in sorted(groups.items())]


def generate_figures(output: Path, rows: list[dict]) -> list[dict]:
    import os
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/virtual_ecu_mpl")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    directory = output / "figures"
    directory.mkdir(exist_ok=True)
    captions = []
    injected = [r for r in rows if r.get("injected") == 1]

    def save(fig, name, caption, counts):
        fig.tight_layout()
        fig.savefig(directory / name, dpi=220)
        plt.close(fig)
        captions.append({"figure": name, "caption": caption, "sample_counts": json.dumps(counts)})

    def distributions(name, key, group_key, ylabel, caption):
        groups = defaultdict(list)
        for row in injected:
            if row.get(key) is not None:
                groups[row[group_key]].append(row[key])
        if not groups:
            captions.append({"figure": name, "caption": "NOT GENERATED: no eligible values", "sample_counts": "{}"})
            return
        labels = sorted(groups)
        fig, ax = plt.subplots(figsize=(max(7, len(labels)*1.1), 4.8))
        ax.boxplot([groups[k] for k in labels], labels=[k.replace("_", " ") + f"\n(n={len(groups[k])})" for k in labels], showmeans=True)
        ax.set_ylabel(ylabel); ax.tick_params(axis="x", rotation=30)
        ax.grid(axis="y", alpha=.25)
        save(fig, name, caption, {k: len(groups[k]) for k in labels})

    distributions("propagation_latency_by_layer.png", "injection_to_plant_latency_ms", "fault_layer",
                  "Injection → plant manifestation (ms)", "Reached plant stages only; pooled descriptive cases, not population estimates.")
    distributions("unsafe_exposure_by_fault_model.png", "critical_exposure_time_ms", "fault_model",
                  "Critical thermal exposure (ms)", "All available exposures, including valid zeroes. Thresholds are experimental.")
    distributions("propagation_depth_by_fault_model.png", "propagation_depth", "fault_model",
                  "v1 propagation depth (0–5)", "Legacy depth retained: internal=1, control=2, command=3, realization=4, plant=5.")
    paired = [r for r in injected if r.get("cross_layer_detection_latency_ms") is not None and r.get("injection_to_plant_latency_ms") is not None]
    if paired:
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        for layer in sorted({r['fault_layer'] for r in paired}):
            points = [r for r in paired if r['fault_layer'] == layer]
            ax.scatter([r['injection_to_plant_latency_ms'] for r in points], [r['cross_layer_detection_latency_ms'] for r in points], alpha=.5, label=f"{layer} (n={len(points)})")
        limit = max(max(r['injection_to_plant_latency_ms'], r['cross_layer_detection_latency_ms']) for r in paired)
        ax.plot([0, max(100, limit)], [0, max(100, limit)], linestyle='--', color='gray')
        ax.set_xlabel('Injection → plant manifestation (ms)'); ax.set_ylabel('Injection → alarm (ms)'); ax.legend(fontsize=8)
        save(fig, 'detection_vs_plant_manifestation.png', 'Only runs with both endpoints; diagonal denotes equal time. Coincident points can overlap.', {'paired': len(paired), 'excluded': len(injected)-len(paired)})
    else:
        captions.append({'figure': 'detection_vs_plant_manifestation.png', 'caption': 'NOT GENERATED: no paired observations', 'sample_counts': '{}'})
    for name, group_key, rate, ylabel in (
        ('containment_by_fault_model.png', 'fault_model', 'containment_success_rate', 'Containment success (%)'),
        ('hazard_rate_by_fault_layer.png', 'fault_layer', 'hazard_entry_rate', 'Hazard entry (%)'),
    ):
        stats = [s for s in grouped(injected, group_key) if s[rate+'_denominator']]
        if not stats:
            captions.append({'figure': name, 'caption': 'NOT GENERATED: no applicable outcomes', 'sample_counts': '{}'})
            continue
        fig, ax = plt.subplots(figsize=(max(7, len(stats)*1.1), 4.8))
        ax.bar(range(len(stats)), [s[rate+'_percent'] for s in stats], color='#3976a8')
        ax.set_xticks(range(len(stats)), [s['group'].replace('_', ' ') + f"\n{s[rate+'_numerator']}/{s[rate+'_denominator']}" for s in stats], rotation=30, ha='right')
        ax.set_ylim(0, 105); ax.set_ylabel(ylabel); ax.grid(axis='y', alpha=.25)
        save(fig, name, 'Denominators exclude baseline and N/A outcomes; deterministic case proportions, not reliability probabilities.', {s['group']: s[rate+'_denominator'] for s in stats})
    write_rows(directory / 'figure_caption_data.csv', captions)
    return captions


def write_report(output: Path, rows: list[dict], overall: dict, figures: list[dict]) -> None:
    lines = ['# Cross-layer safety v2 campaign', '',
             'Engineering research evidence from deterministic model runs. No detector retuning, OEM calibration, ISO 26262 compliance, or population reliability claim.', '',
             f"Total runs: {len(rows)}; injected runs: {overall['injected_run_count']}; activation windows: {overall['fault_injection_count']}.", '',
             '| Metric | Successes / eligible runs | Percent |', '| --- | --- | --- |']
    for rate in RATE_FIELDS:
        percent = overall[rate+'_percent']
        lines.append(f"| {rate} | {overall[rate+'_numerator']} / {overall[rate+'_denominator']} | {'N/A' if percent is None else f'{percent:.2f}%'} |")
    lines += ['', 'Rates exclude baseline and unavailable outcomes. Hazard rates also exclude hazards that existed before injection. Latency means/medians exclude absent endpoints. Zero exposures and same-tick zero latencies are valid observations.', '',
              'Grouped rates, denominators, latency sample counts, exposure distributions, and v1 depth distributions are in fault_layer_summary.csv, fault_model_summary.csv, fault_behavior_summary.csv, and operating_profile_summary.csv.', '',
              '## Observed cases', '']
    for title, predicate in (
        ('Undetected', lambda r: r.get('injected') == 1 and r.get('detected') == 0),
        ('Silent internal corruption', lambda r: r.get('silent_corruption') == 1),
        ('No plant manifestation', lambda r: r.get('injected') == 1 and r.get('plant_manifestation') == 0),
        ('Hazard entered', lambda r: r.get('hazard_entered') == 1),
        ('Containment failed', lambda r: r.get('containment_success') == 0),
    ):
        selected = [r for r in rows if predicate(r)]
        lines += [f"### {title}: {len(selected)} runs", '',
                  ', '.join(r['run_id'] for r in selected[:12]) or 'None observed.',
                  'Complete classifications and timings are retained in campaign_runs.csv.', '']
    lines += ['## Figures', '']
    for fig in figures:
        lines += [f"- {fig['figure']}: {fig['caption']} Counts: {fig['sample_counts']}"]
    lines += ['', '## Definitions and limits', '',
              'Hazard is sustained critical temperature for the configured consecutive exposure allowance. Containment requires temperature below warning for the configured hold, with a protective mode or resolved fault effects; prior hazard makes containment fail. Alarm is not containment. FTTI starts at injection and includes the hold interval. Results are horizon-limited.', '',
              'Transient task delay is discrete and non-preemptive: one pending job, current inputs at eventual execution, releases while pending discarded. Sensor replay retains the historical packet acquisition timestamp. Queued delayed samples are flushed at recovery. See architecture documentation for exact rules.', '',
              'All current faults are deterministic: seeds are recorded, not used to invent variation. No stochastic replication or confidence intervals are claimed. Candidate matrix comparisons are descriptive and include unequal fault severities/durations.', '',
              'Legacy detector truth/metadata exceptions remain unchanged. New runtime_observation_t excludes fault labels, injection timing, plant truth, reference state, and hazard outcomes. No new detector decision logic was introduced.', '',
              'Reproduce with the captured study_config.json and commands.json. Original v1 evidence is preserved.', '']
    (output / 'cross_layer_safety_report.md').write_text('\n'.join(lines), encoding='utf-8')


def run_campaign(config_path: Path = DEFAULT_STUDY, output: Path = DEFAULT_CAMPAIGN_DIR) -> list[dict]:
    output = output.resolve()
    protected = (PROJECT_ROOT / 'results/cross_layer_safety_v1').resolve()
    if output == protected or protected in output.parents:
        raise ValueError('Campaign output must not overwrite v1 evidence')
    config = read_study(config_path)
    runs = expand_runs(config)
    if not runs or len(runs) > config.get('max_runs', 300):
        raise ValueError(f"Campaign has {len(runs)} runs; empty or exceeds max_runs")
    # Construct the whole matrix before executing to surface configuration errors.
    commands = [command_for_run(run, config, output / 'raw' / (run['run_id']+'.csv')) for run in runs]
    subprocess.run(['make'], cwd=PROJECT_ROOT, check=True)
    (output / 'raw').mkdir(parents=True, exist_ok=True)
    # Remove only runner-owned prior traces; GUI and v1 evidence live elsewhere.
    for old in (output / 'raw').glob('run_*.csv'):
        old.unlink()
    for name in ('propagation_latency_by_layer.png', 'detection_vs_plant_manifestation.png',
                 'containment_by_fault_model.png', 'unsafe_exposure_by_fault_model.png',
                 'propagation_depth_by_fault_model.png', 'hazard_rate_by_fault_layer.png'):
        (output / 'figures' / name).unlink(missing_ok=True)
    (output / 'study_config.json').write_text(json.dumps(config, indent=2)+'\n')
    (output / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    rows = []
    for index, (run, command) in enumerate(zip(runs, commands), 1):
        completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if completed.returncode:
            raise RuntimeError(f"{run['run_id']}: {completed.stderr or completed.stdout}")
        raw = Path(command[1])
        summary = load_summary(raw)
        row = {"run_id": run['run_id'], "operating_profile": run['profile']['id'],
               "detector": run['detector']['algorithm'], "detector_action": run['detector']['action'],
               "raw_csv": str(raw), "configuration": json.dumps(run['parameters'], sort_keys=True),
               **summary}
        if run['model'] in ('sensor_bias','pump_degraded','fan_stuck_off'):
            row['fault_model'] = run['model']
        rows.append(row)
        if index % 20 == 0 or index == len(runs):
            print(f"Completed {index}/{len(runs)} runs", flush=True)
    write_rows(output / 'campaign_runs.csv', rows)
    overall = group_statistics(rows)
    write_rows(output / 'overall_summary.csv', [overall])
    for key, filename in (('fault_layer','fault_layer_summary.csv'), ('fault_model','fault_model_summary.csv'),
                          ('fault_behavior','fault_behavior_summary.csv'), ('operating_profile','operating_profile_summary.csv')):
        write_rows(output / filename, grouped(rows, key))
    write_rows(output / 'propagation_summary.csv', rows, ('run_id',*STAGES,'propagation_depth','max_propagation_stage','propagation_path_signature'))
    write_rows(output / 'hazard_ftti_summary.csv', rows, ('run_id','hazard_entered','hazard_entry_ms','hazard_exit_ms','critical_exposure_time_ms','ftti_met','detected_before_hazard','safe_state_before_hazard','preexisting_hazard'))
    write_rows(output / 'containment_summary.csv', rows, ('run_id','detected','safe_state_reached','hazard_entered','containment_success','containment_time_ms','containment_latency_ms','ftti_met'))
    write_rows(output / 'silent_corruption_summary.csv', rows, ('run_id','fault_layer','fault_model','internal_corruption','detected','plant_manifestation','hazard_entered','silent_corruption'))
    figures = generate_figures(output, rows)
    write_report(output, rows, overall, figures)
    hashes = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((output/'raw').glob('*.csv'))}
    (output/'raw_sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    return rows
