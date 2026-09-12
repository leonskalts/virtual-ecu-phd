#!/usr/bin/env python3
"""Run the source-frozen v5 final validation campaign and evidence analysis."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.validation_v5_design import OUTPUT
from virtual_ecu.validation_v5_runner import run

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,default=OUTPUT);p.add_argument('--resume',action='store_true');p.add_argument('--simulations-only',action='store_true');args=p.parse_args()
 rows,ablations=run(args.output_dir,args.resume)
 if not args.simulations_only:
  from virtual_ecu.validation_v5_design import load_config
  from virtual_ecu.validation_v5_recovery import run_recovery
  from virtual_ecu.validation_v5_overhead import measure
  from virtual_ecu.validation_v5_report import write_package
  from virtual_ecu.validation_v5_package import finalize
  run_recovery(args.output_dir,load_config(),args.resume)
  measure(args.output_dir)
  write_package(args.output_dir,rows,ablations)
  finalize(args.output_dir.resolve())
 print(f'V5 holdout: {len(rows)} configured simulations; {args.output_dir}')
if __name__=='__main__':main()
