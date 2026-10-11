#!/usr/bin/env python3
"""Export compact C inference parameters and verify against fitted inference."""
import json,pickle,ctypes,subprocess
from pathlib import Path
import run_ml_assisted_clodsf as d
import numpy as np
from scipy.special import expit
B=d.B;O=d.O

def main():
 config=json.loads((O/'calibration.json').read_text());p=pickle.loads((O/'provider_svm.pkl').read_bytes());sc,sv=p[0],p[1];f=config['platt'];linear=sv.kernel=='linear'
 record=dict(feature_names=d.FEATURES,type=sv.kernel,mean=sc.mean_.tolist(),scale=sc.scale_.tolist(),weights=sv.coef_[0].tolist() if linear else [],support_vectors=[] if linear else sv.support_vectors_.tolist(),dual=[] if linear else sv.dual_coef_[0].tolist(),intercept=float(sv.intercept_[0]),gamma=float(sv._gamma),platt_slope=f['slope'],platt_intercept=f['intercept'],alpha=config['provider']['alpha'],gate=config['provider']['gate'])
 d.dump(O/'runtime_model.json',record)
 class Model(ctypes.Structure):
  _fields_=[('rbf',ctypes.c_uint),('n_support',ctypes.c_uint),('mean',ctypes.c_double*12),('scale',ctypes.c_double*12),('weight',ctypes.c_double*12),('support',ctypes.POINTER(ctypes.c_double)),('dual',ctypes.POINTER(ctypes.c_double)),('intercept',ctypes.c_double),('gamma',ctypes.c_double),('platt_slope',ctypes.c_double),('platt_intercept',ctypes.c_double)]
 subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-Iinclude','src/v7_3/ml_sensor_weak.c','-lm','-o',str(B/'native_model.so')],check=True)
 lib=ctypes.CDLL(str(B/'native_model.so'));lib.ml_sensor_confidence.argtypes=[ctypes.POINTER(Model),ctypes.POINTER(ctypes.c_double)];lib.ml_sensor_confidence.restype=ctypes.c_double
 m=Model();m.rbf=int(not linear);m.n_support=0 if linear else len(sv.support_)
 for key,value in [('mean',sc.mean_),('scale',sc.scale_),('weight',sv.coef_[0] if linear else np.zeros(12))]:setattr(m,key,(ctypes.c_double*12)(*value))
 support=np.ascontiguousarray(sv.support_vectors_) if not linear else np.zeros((1,12));dual=np.ascontiguousarray(sv.dual_coef_[0]) if not linear else np.zeros(1);m.support=support.ctypes.data_as(ctypes.POINTER(ctypes.c_double));m.dual=dual.ctypes.data_as(ctypes.POINTER(ctypes.c_double));m.intercept=record['intercept'];m.gamma=record['gamma'];m.platt_slope=f['slope'];m.platt_intercept=f['intercept']
 checked=0;error=0
 for row,a in d.dataset('CALIBRATION'):
  x=np.ascontiguousarray(a['features'][::60]);expected=expit(f['slope']*d.margin(p,x)+f['intercept']);actual=np.array([lib.ml_sensor_confidence(ctypes.byref(m),v.ctypes.data_as(ctypes.POINTER(ctypes.c_double))) for v in x]);error=max(error,float(np.max(np.abs(actual-expected))));checked+=len(x)
 assert error<1e-8,error
 d.dump(O/'native_inference_test.json',dict(passed=True,checked_frames=checked,max_confidence_error=error,parameter_struct_bytes=ctypes.sizeof(Model),support_parameter_bytes=0 if linear else support.nbytes+dual.nbytes,no_runtime_python_required=True))
 if linear:d.h.write(O/'feature_weights.csv',[dict(feature=n,standardized_weight=float(w),raw_feature_weight=float(w/scale)) for n,w,scale in zip(d.FEATURES,sv.coef_[0],sc.scale_)])
 print('C INFERENCE PARITY',checked,error,flush=True)
if __name__=='__main__':main()
