#!/usr/bin/env python3
import json,subprocess,shutil,sys
import run_benign_alarm as t
import regress_digital_integrity as reg

def main():
 t.verify();r=json.loads((t.O/'report.json').read_text());assert not (t.B/'finalization_started').exists();(t.B/'finalization_started').write_text(t.old.d.r.now())
 # Reuse established regression runner, retaining its backup/restore isolation.
 original=t.old;original.B=t.B;original.O=t.O;original.verify=t.verify
 reportpath=t.O/'report.json';temporary=dict(r,promoted=r['retained']);t.dump(reportpath,temporary)
 try:reg.main()
 finally:t.dump(reportpath,r)
 t.verify();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head==json.loads((t.O/'registration.json').read_text())['head'];record=json.loads((t.O/'study_record.json').read_text());record['regression']=json.loads((t.O/'regression.json').read_text());record['completed_utc']=t.old.d.r.now();record['protected_files']=len(json.loads((t.B/'protected.json').read_text()));record['test_output']=(t.B/'tests.log').read_text();t.dump(t.O/'study_record.json',record)
 lines=['# Validation record','',f'HEAD unchanged: {head}.',f"{record['protected_files']} original files unchanged; GUI, integrity/M2, Hybrid/HETIA, physics/control/fault and old results preserved.",'1255seen historical reconstruction runs only for root-cause audit; exact original A2 metric parity. Seven preselected new TRAIN cases additionally exercised native gate smoke checks before the registered campaign. NEW TRAIN2400/CAL2400 selected one predefined configuration; VALID3600(1200fault/2400benign) untouched until source/model/selection lock. No validation retuning or alternate-candidate scoring. Frozen SVM unchanged.','No raw traces retained. No unseen, commit or push.',json.dumps(record['regression'],indent=2),record['test_output']]
 (t.O/'validation_record.md').write_text('\n'.join(lines)+'\n')
 for p in t.B.iterdir():
  if p.is_dir() and (p.name.startswith('work_') or p.name in ['audit_work','binary_backup','smoke']):shutil.rmtree(p)
  elif p.name.endswith('_rows.json'):p.unlink()
 t.dump(t.O/'artifact_hashes.json',{p.name:t.sha(p) for p in t.O.iterdir() if p.is_file() and p.name!='artifact_hashes.json'});print('FINALIZED',sum(p.stat().st_size for p in t.O.iterdir() if p.is_file()),'bytes',flush=True)
if __name__=='__main__':main()
