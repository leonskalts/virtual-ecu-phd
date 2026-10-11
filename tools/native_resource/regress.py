"""Regression checks with restoration of existing scientific build products."""
import os,sys,json,subprocess,tempfile,shutil,hashlib,gzip
from pathlib import Path
sys.path[:0]=['python','/tmp/clo-ml-deps']
from virtual_ecu.final_reproducibility import legacy_regression,rtl_regression
R=Path.cwd();O=R/'results/native_resource_benchmark';B=Path('/tmp/clo-native-resource');backup=B/'regression_backup';backup.mkdir(exist_ok=True)
paths=list((R/'src').rglob('*.o'))+[p for p in R.glob('virtual_ecu*') if p.is_file()]
for p in paths:
 q=backup/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
result={}
try:
 env=dict(os.environ,PYTHONPATH=str(R/'python')+':/tmp/clo-ml-deps',PYTHONPYCACHEPREFIX='/tmp/clo-native-resource/pycache')
 cmds=[('build',['make','-B','-f','clo_dsf_revised.mk','-j4']),('compile',[sys.executable,'-m','compileall','-q','python','scripts','tests','tools/native_resource']),('tests',[sys.executable,'-m','unittest','discover','-s','tests']),('diff_check',['git','diff','--check'])]
 for name,cmd in cmds:
  print(name,flush=True);p=subprocess.run(cmd,capture_output=True,text=True,env=env);(B/(name+'.log')).write_text(p.stdout+p.stderr);result[name]=p.returncode
  if p.returncode:raise RuntimeError(name+': '+p.stderr[-3000:])
 with tempfile.TemporaryDirectory(prefix='native-regression-') as td:
  result['legacy']=legacy_regression(Path(td));print('legacy',result['legacy'],flush=True)
  result['rtl']=rtl_regression(Path(td));print('rtl',result['rtl'],flush=True)
finally:
 for p in paths:shutil.copy2(backup/p.relative_to(R),p)
 (O/'regression.json').write_text(json.dumps(result,indent=2))
 for p in B.glob('*.log'):
  with gzip.open(O/(p.name+'.gz'),'wb') as f:f.write(p.read_bytes())
manifest=json.loads((O/'preservation.json').read_text() if (O/'preservation.json').exists() else gzip.decompress((O/'preservation.json.gz').read_bytes()));bad=[]
for name,h in manifest.items():
 p=Path(name)
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:bad.append(name)
result['preserved_files']=len(manifest);result['changed_preexisting_files']=bad;result['frozen_results_GUI_Hybrid_unchanged']=not bad
(O/'regression.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
assert not bad
