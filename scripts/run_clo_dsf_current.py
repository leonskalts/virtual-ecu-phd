#!/usr/bin/env python3
"""Run the one compact CURRENT development/validation campaign."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_current import run
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--prechange-source',required=True,type=Path)
    parser.add_argument('--replace-current',action='store_true')
    args=parser.parse_args()
    run(args.prechange_source,args.replace_current)
