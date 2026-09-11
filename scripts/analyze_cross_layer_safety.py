#!/usr/bin/env python3
"""Reanalyze v2 evidence without rerunning or modifying the simulator."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.cross_layer_analysis import analyze_campaign, DEFAULT_INPUT, DEFAULT_OUTPUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = analyze_campaign(args.input, args.output)
    print(f'Analyzed {len(rows)} runs; evidence package: {args.output}')


if __name__ == '__main__':
    main()
