#!/usr/bin/env python3
"""Generate a cross-layer propagation report from a raw virtual ECU CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from propagation_report import (
    build_propagation_report,
    propagation_csv_rows,
    read_csv_rows,
    save_propagation_plot,
    write_propagation_csv,
    write_propagation_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a propagation timeline CSV/text/figure bundle from a raw virtual ECU campaign CSV."
    )
    parser.add_argument(
        "input_csv",
        help="Path to the raw time-series campaign CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated outputs. Defaults to a sibling '<campaign>_propagation' folder.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional display label for the report title and summary section.",
    )
    return parser.parse_args()


def default_output_dir(input_csv: Path) -> Path:
    return input_csv.parent / f"{input_csv.stem}_propagation"


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    rows = read_csv_rows(input_csv)
    if not rows:
        raise ValueError(f"No rows found in {input_csv}")

    report = build_propagation_report(rows)
    label = args.label or str(report["campaign_label"] or report["campaign_id"] or input_csv.stem)
    output_dir = Path(args.output_dir) if args.output_dir is not None else default_output_dir(input_csv)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "propagation_timeline.csv"
    summary_path = output_dir / "propagation_summary.txt"
    figure_path = output_dir / "propagation_timeline.png"

    write_propagation_csv(csv_path, propagation_csv_rows("run", report))
    write_propagation_summary(summary_path, [report], [label])
    save_propagation_plot([label], [report], figure_path, title=f"{label} Cross-Layer Propagation Timeline")

    print(f"Wrote propagation report bundle to {output_dir}")
    print(f"  - {csv_path}")
    print(f"  - {summary_path}")
    print(f"  - {figure_path}")


if __name__ == "__main__":
    main()
