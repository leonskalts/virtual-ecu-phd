#!/usr/bin/env python3
"""Run a YAML/JSON-configured cross-layer automotive safety campaign."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from virtual_ecu.cross_layer_campaign import DEFAULT_STUDY, DEFAULT_CAMPAIGN_DIR, run_campaign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', nargs='?', type=Path, default=DEFAULT_STUDY)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_CAMPAIGN_DIR)
    args = parser.parse_args()
    rows = run_campaign(args.study, args.output_dir)
    print(f'Campaign complete: {len(rows)} runs in {args.output_dir}')


if __name__ == '__main__':
    main()
