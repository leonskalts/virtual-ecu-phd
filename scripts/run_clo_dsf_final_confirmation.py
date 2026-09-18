#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_final_confirmation import run
if __name__=='__main__':run()
