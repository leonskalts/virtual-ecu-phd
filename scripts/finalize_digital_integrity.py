#!/usr/bin/env python3
import json,shutil,subprocess
import run_digital_integrity as t

def main():
 t.verify();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head==json.loads((t.O/'registration.json').read_text())['head'];reg=json.loads((t.O/'regression.json').read_text());assert reg['old_scientific_and_results_unchanged']
 record=json.loads((t.O/'study_record.json').read_text());record['failure_test_source']=(t.B/'failure_matrix.c').read_text();record['boundary_parity']=json.loads((t.O/'boundary_parity.json').read_text());record['regression']=reg;record['protected_file_count']=len(json.loads((t.B/'protected.json').read_text()));record['final_head']=head;record['completed_utc']=t.d.r.now();t.dump(t.O/'study_record.json',record)
 lines=['# Validation record','',f'HEAD unchanged: {head}.',f"{record['protected_file_count']} pre-existing source/result/GUI hashes unchanged. Hybrid/HETIA and legacy evidence preserved.",'New deterministic8400-case grouped TRAIN/CAL/VALID development only. VALID1200fault+1200benign. Historical90 separately labeled SEEN regression; never used for selection.','Protocol/manifest registered before campaign; non-sensor tick-alignment amendment followed a rejected invocation before any simulation outcomes.11 TRAIN smoke cases were run for instrumented/uninstrumented parity; primary campaign then executed once per case. No validation reruns or tuning.','Provider fixed before TRAIN. SVM model and empirical1% threshold CAL-selected and locked before VALID. Full method metrics and configuration manifest retained; no raw traces retained.',json.dumps(reg,indent=2),'No commit/push/unseen. Isolated witness protection is an explicit architecture assumption, not enforced by ordinary C memory. CRC is not an authenticity guarantee against consistent data+witness compromise.']
 (t.O/'validation_record.md').write_text('\n'.join(lines)+'\n')
 for p in t.B.iterdir():
  if p.is_dir() and (p.name.startswith(('work','smoke','binary_backup')) or p.name=='tapes'):shutil.rmtree(p)
  elif p.name.endswith(('_rows.json','_evaluated.json')):p.unlink()
 t.dump(t.O/'artifact_hashes.json',{p.name:t.sha(p) for p in t.O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'});print('FINALIZED',sum(p.stat().st_size for p in t.O.iterdir() if p.is_file()),'bytes',flush=True)
if __name__=='__main__':main()
