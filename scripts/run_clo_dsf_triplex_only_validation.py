#!/usr/bin/env python3
"""Evaluation-only continuation of the existing locked campaign; no A2 linkage."""
import csv, inspect, json, hashlib, subprocess
from pathlib import Path
import run_clo_dsf_triplex as t
B=Path('/tmp/clo-triplex-only-validation'); prior=Path('/tmp/clo-triplex-latch')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not B.exists(), 'Never rerun this validation'
 lock=json.loads((prior/'lock.json').read_text())
 assert all(sha(Path(p))==v for p,v in lock['files'].items())
 assert not (prior/'FAULT_VALIDATION_started').exists()
 ss=json.loads((prior/'specs.json').read_text())
 manifest=list(csv.DictReader((t.OUT/'campaign_manifest.csv').open()))
 assert len(ss)==len(manifest)==2400
 for s,r in zip(ss,manifest):
  assert all(str(v)==r[k] for k,v in s.items())
 selected=[s for s in ss if s['partition']=='VALIDATION' and s['origin']!='NONE' and s['origin']!='NORMAL']
 # The manifest uses BENIGN for non-injected controls.
 selected=[s for s in selected if s['origin']!='BENIGN']
 assert len(selected)==480
 benign=t.h.records(prior/'BENIGN_VALIDATION_rows.csv')
 for m in ['A0','A1']:
  rr=[r for r in benign if r['method']==m]
  assert len(rr)==120 and not any(r['false_alarm'] or r['wrong_localized_runtime_samples'] for r in rr)
 B.mkdir()
 paths=list(Path('src').rglob('*'))+list(Path('include').rglob('*'))+[Path('presets/gui_session_state.json')]
 snapshot={str(p):sha(p) for p in paths if p.is_file()}
 (B/'initial.json').write_text(json.dumps(snapshot,indent=2))
 (B/'specs.json').write_bytes((prior/'specs.json').read_bytes())
 (B/'lock.json').write_bytes((prior/'lock.json').read_bytes())
 protocol='''# Triplex-only validation continuation\n\nAuthorized evaluation-only continuation: A2 is permanently rejected. Run the existing 480 fault VALIDATION cases exactly once using locked A0/A1 harness and shared observations. Reuse the completed 120 benign controls. No A2 linkage, no parameter changes, no unseen campaign. Inspect outcomes only after all 480 complete.\n\nOriginal domain NONE/A/B/AB: 400 faults. Expanded: all 480 faults. Promotion requires original detection >=91%, benign <=1%, zero wrong confident origins, plant-conditioned >=95%, no paired timing/communication/effective-memory losses, AB common >=90%. Report expanded separately. No changes after results; run full regression only if gates pass.\n'''
 (t.OUT/'triplex_only_protocol.md').write_text(protocol+'\nHEAD: '+subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()+'\nManifest SHA256: '+sha(t.OUT/'campaign_manifest.csv')+'\n')
 (B/'protocol.sha256').write_text(sha(t.OUT/'triplex_only_protocol.md'))
 # Reuse the exact locked A0/A1 execution body; only restrict its partition selection.
 source=inspect.getsource(t.run)
 source=source.replace("selected=[s for s in ss if s['partition']==part]", "selected=[s for s in ss if s['partition']==part and s['origin'] not in ['NONE','NORMAL','BENIGN']]")
 assert source!=inspect.getsource(t.run)
 t.B=B
 exec(compile(source,__file__,'exec'),t.__dict__)
 t.run('VALIDATION')
 assert all(sha(Path(p))==v for p,v in lock['files'].items())
 assert all(sha(Path(p))==v for p,v in snapshot.items())
 (B/'integrity_passed').write_text('scientific files, locked protocol/manifest and GUI unchanged')
 print('All 480 completed; outcomes may now be inspected.',flush=True)
if __name__=='__main__':main()
