#!/usr/bin/env python3
"""Run paired timing-monitor and communication-response studies in v4 output."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.runtime_safety_study import run_studies,TIMING_STUDY,COMMUNICATION_STUDY,DEFAULT_OUTPUT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timing-study',type=Path,default=TIMING_STUDY)
    parser.add_argument('--communication-study',type=Path,default=COMMUNICATION_STUDY)
    parser.add_argument('--output-dir',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    rows=run_studies(args.timing_study,args.communication_study,args.output_dir)
    print(f'Runtime safety study complete: {len(rows)} runs in {args.output_dir}')


if __name__=='__main__':main()
