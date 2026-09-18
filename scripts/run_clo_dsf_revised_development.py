#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_revised_development import run
if __name__=='__main__':run()
