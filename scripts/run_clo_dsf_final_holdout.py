#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_holdout import run
if __name__=='__main__':
 if sys.argv[1:] not in [[],['--repair-profile-order']]:raise SystemExit('Usage: run_clo_dsf_final_holdout.py [--repair-profile-order]')
 run(repair_profile_order=sys.argv[1:]==['--repair-profile-order'])
