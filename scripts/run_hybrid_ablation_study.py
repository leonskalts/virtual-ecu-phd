#!/usr/bin/env python3
"""Report whether faithful Hybrid Adaptive Kalman ablation variants exist."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "hybrid_ablation_study"
EXPECTED_VARIANTS = (
    "hybrid_ablation_no_sensor_freshness",
    "hybrid_ablation_no_actuator_consistency",
    "hybrid_ablation_no_calibration_evidence",
    "hybrid_ablation_no_thermal_response",
    "hybrid_ablation_kalman_residual_only",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check for explicit component-disable Hybrid detector variants. "
            "No quantitative ablation is inferred when variants are absent."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = (
        PROJECT_ROOT / "include" / "detection_algorithm.h",
        PROJECT_ROOT / "src" / "detection_algorithm.c",
        PROJECT_ROOT / "src" / "main.c",
    )
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    available = [variant for variant in EXPECTED_VARIANTS if variant in source_text]
    missing = [variant for variant in EXPECTED_VARIANTS if variant not in available]
    implemented = not missing

    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quantitative_ablation_available": implemented,
        "existing_detector_unchanged": True,
        "expected_ablation_variants": list(EXPECTED_VARIANTS),
        "available_ablation_variants": available,
        "missing_ablation_variants": missing,
        "source_files_checked": [str(path.relative_to(PROJECT_ROOT)) for path in sources],
        "decision": (
            "Explicit ablation variants are available; a quantitative runner still "
            "requires a validated scenario integration."
            if implemented
            else "Quantitative ablation omitted because explicit component-disable "
            "variants are not implemented in the runtime detector."
        ),
    }
    (output_dir / "ablation_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )

    readme = """# Hybrid Adaptive Kalman Ablation Status

No quantitative ablation matrix was generated.

The current runtime detector exposes `hybrid_adaptive_kalman` as one integrated
implementation, but it does not expose the requested component-disable variants.
Disabling evidence only in post-processing would not faithfully reproduce the
detector's state evolution, confirmation logic, labels, or online execution.
Adding new C detector variants would expand detector behavior and requires a
separate design and validation task.

Accordingly, this workflow preserves the existing detector unchanged and records
the missing evidence explicitly. It does not create inferred coverage, latency,
or clean-alarm numbers.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Hybrid ablation status written to: {output_dir}")
    print(f"Quantitative ablation available: {implemented}")
    if missing:
        print("Missing explicit variants: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
