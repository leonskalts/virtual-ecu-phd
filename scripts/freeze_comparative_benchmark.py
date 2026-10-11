#!/usr/bin/env python3
"""Seal full reproducibility metadata; never change a selected configuration."""
import sys,json,pickle,subprocess,platform
from pathlib import Path
import run_comparative_benchmark as r
sys.path.insert(0,'/tmp/clo-ml-deps')
import sklearn,scipy
original_dump=r.dump

def metadata_dump(path,data):
 if path==r.OUT/'method_freeze.json':
  models=pickle.loads((r.B/'models.pkl').read_bytes())
  evidence=list(r.be.CHANNELS)
  full_features=evidence+[c+'_available' for c in evidence]
  hashes={p:r.sha(r.OUT/p) for p in ['train_calibration_manifest.csv','validation_manifest.csv']}
  for name,m in data['methods'].items():
   m['training_data_hashes']={'train_calibration_manifest':hashes['train_calibration_manifest.csv'],'source_manifest':r.sha(r.ROOT/'results/clo_dsf_current/multirate_manifest.csv')}
   m['calibration_data_hashes']=m['training_data_hashes'].copy()
   m['features']=full_features if name=='SVM' else evidence+['availability','instantaneous_origin_subsets']
   m['parameters']=m.get('parameters',{'source':'protocol.md; frozen implementation and configuration hashes'})
   m['thresholds']=m.get('thresholds',{'source':'protocol.md; selected_parameters.json for calibrated methods'})
  data['methods']['OR']['parameters']={'alarm':'any available e>=.5','origin':'single qualifying singleton, else UNKNOWN'}
  data['methods']['OR']['thresholds']={'provider':.5}
  data['methods']['Weighted Sum']['parameters']=data['selection']
  data['methods']['Weighted Sum']['thresholds']={k:v['threshold'] for k,v in data['selection'].items()}
  data['methods']['Plain DS']['parameters']={'bpa':'m(A)=e,m(Theta)=1-e; origin simple support on provider subset','combination':'classical normalized conjunctive','temporal_state':False,'total_origin_conflict':'UNKNOWN'}
  data['methods']['Plain DS']['thresholds']={'detection':.5,'origin_betp':.55,'origin_margin':.15,'origin_ignorance_max':.5}
  data['methods']['SVM']['parameters']={}
  for arch in [0,1]:
   model=models[arch][data['selection'][str(arch)]['svm']]
   data['methods']['SVM']['parameters'][str(arch)]={'svc':model[-1].get_params(),'scaler_mean':model[0].mean_.tolist(),'scaler_scale':model[0].scale_.tolist()}
  data['methods']['SVM']['thresholds']={'decision_function':0}
  cfg=dict(line.split('=',1) for line in r.h.c.CONFIG.read_text().splitlines() if line and not line.startswith('#'))
  for name in ['CURRENT','TRIPLEX']:
   data['methods'][name]['parameters']={'configuration':cfg,'provider_and_logic':'unchanged frozen scientific_files','temporal_state':True}
   data['methods'][name]['thresholds']={k:v for k,v in cfg.items() if 'threshold' in k or 'limit' in k or 'persistence' in k}
  data['software']={'python':platform.python_version(),'numpy':r.np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'gcc':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0]}
  for p in [Path(__file__),r.ROOT/'scripts/report_comparative_benchmark.py',r.ROOT/'tests/test_comparative_backends.py',r.ROOT/'docs/comparative_benchmark.md']:
   data['files'][str(p)]=r.sha(p)
 original_dump(path,data)

if __name__=='__main__':
 r.dump=metadata_dump
 r.freeze_unseen()
