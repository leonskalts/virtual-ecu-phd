#!/usr/bin/env python3
"""Run the preregistered v7 development study; refuses silent overwrite."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.clo_dsf_development import run
if __name__=='__main__': run()
