#!/usr/bin/env python3
"""Freeze, audit and reproduce accepted evidence without modifying v1–v5 folders."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.final_evidence import OUTPUT
from virtual_ecu.final_reproducibility import quick, analysis, full


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--quick-check',action='store_true',help='Default: build, tests, small replay, immutable evidence and claim checks')
    modes.add_argument('--analysis-only',action='store_true',help='Regenerate final tables/figures/claims/report from accepted evidence')
    modes.add_argument('--full',action='store_true',help='Many simulations: rerun accepted v5, legacy and RTL workflows in isolated output')
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=parser.parse_args()
    try:
        (full if args.full else analysis if args.analysis_only else quick)(args.output_dir.resolve())
    except (OSError,ValueError,RuntimeError,AssertionError) as exc:
        parser.exit(1,f'Reproducibility check failed: {exc}\n')
    print(f'Cross-layer v6 package ready: {args.output_dir.resolve()}')

if __name__=='__main__':main()
