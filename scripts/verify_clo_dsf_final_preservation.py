#!/usr/bin/env python3
"""Read-only preservation audit plus isolated accepted scientific regressions."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from virtual_ecu.final_evidence import verify_frozen
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression,representative_replay
OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation'
def verify():
 original=json.loads(Path('/tmp/clo-final-preflight/existing_hashes.json').read_text());changed=[]
 for name,digest in original.items():
  p=ROOT/name
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
 assert not changed,changed
 subprocess.run(['python3','scripts/package_clo_dsf_candidate2_development.py','--verify'],cwd=ROOT,check=True)
 return dict(existing_files=len(original),changed_files=changed,user_session_unchanged=True,accepted=verify_frozen())
def run():
 result=verify()
 if '--full' in sys.argv:result.update(legacy_cases=legacy_regression(OUT),rtl_cases=rtl_regression(OUT),v5_replays=representative_replay(OUT))
 result['status']='PASS';(OUT/'validation/preservation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':run()
