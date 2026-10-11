"""Causal common-input RF features. No predictions or case metadata accepted."""
import numpy as np
# Same trusted observation fields consumed by the frozen providers/core. Diagnostic
# alarm/id/safety outputs are excluded: they are unused by the frozen core.
OBS = ['time_ms','coolant_measured_c','sample_timestamp_ms','sample_age_ms',
 'control_target_c','pump_command','fan_command','pump_actual','fan_actual',
 'control_execution_ms','engine_load','ambient_c','vehicle_speed_kph',
 'sample_freshness_ok','sample_expected_period_ms','target_register_c',
 'target_shadow_c','target_shadow_valid','memory_check_ms','memory_check_valid',
 'memory_check_failed','source_c','source_previous_c','source_ms','source_previous_ms',
 'source_valid','source_previous_valid','reference_c','reference_ms','reference_enabled',
 'reference_valid','reference_failed']
TIMING=['task_id','time_ms','period_ms','relative_deadline_ms','release_sequence',
 'execution_sequence','current_release_ms','job_release_ms','actual_start_ms',
 'actual_completion_ms','last_successful_execution_ms','execution_age_ms',
 'job_outstanding','missed_expected_execution','deadline_exceeded','cancelled_release_count']
C=['value_c','previous_c','sample_ms','previous_ms','valid','previous_valid','failed']
EXTRA=['triplex_strength','triplex_ambiguous','triplex_qualified','triplex_aligned_c',
 'qualified_sensor_strength','local_sensor_strength',
 'integrity_available','integrity_bad','integrity_status_A','integrity_status_B',
 'integrity_status_C','integrity_held_fail']
FIELDS=OBS+['timing.'+x for x in TIMING]+['C.'+x for x in C]+EXTRA
CLASSES=['NORMAL','MEMORY','TIMING','COMMUNICATION','SENSOR_CONTROL','ACTUATOR']
TIME_FIELDS={'sample_timestamp_ms','control_execution_ms','memory_check_ms','source_ms',
 'source_previous_ms','reference_ms','timing.time_ms','timing.current_release_ms',
 'timing.job_release_ms','timing.actual_start_ms','timing.actual_completion_ms',
 'timing.last_successful_execution_ms','C.sample_ms','C.previous_ms'}

def schema():
 return dict(raw_fields=FIELDS,excluded=['diagnostic_id','safety_state','detector_alarm',
 'CLOVER alarm/origin/beliefs/direct_origins','injected origin/start/duration','offline plant propagation'],
 feature_encoding='All packet fields except absolute time; timestamp fields become signed age (negative sentinel retained); explicit finite masks. Include six strength/availability/origin-support vectors. Add 10-frame and 50-frame causal means/maxima of six masked provider strengths. No absolute case clock, future samples or outcome fields.',
 origin_support='Provider support sets, not CLOVER estimated origin. Captured before DS fusion.',
 classes=CLASSES)

def features(packet,e):
 a=np.asarray(packet,float);assert a.shape[1]==len(FIELDS)
 assert np.array_equal(a[:,0],e.time_ms)
 v=a[:,1:].copy();names=FIELDS[1:]
 for j,name in enumerate(names):
  if name in TIME_FIELDS:v[:,j]=np.where(v[:,j]>=0,a[:,0]-v[:,j],v[:,j])
 valid=np.isfinite(v);v=np.where(valid,v,0.)
 pieces=[v,valid.astype(float),e.values,e.available.astype(float),e.origin_subset.astype(float)]
 for width in [10,50]:
  padded=np.pad(e.values,((width-1,0),(0,0)))
  avail=np.pad(e.available.astype(float),((width-1,0),(0,0)))
  windows=np.lib.stride_tricks.sliding_window_view(padded,width,axis=0)
  counts=np.lib.stride_tricks.sliding_window_view(avail,width,axis=0).sum(axis=-1)
  mean=np.divide(windows.sum(axis=-1),counts,out=np.zeros_like(e.values),where=counts>0)
  pieces.extend([mean,windows.max(axis=-1)])
 return np.column_stack(pieces)

def decisions(prob,alarm_threshold,confidence,margin):
 p=np.asarray(prob,float);assert p.ndim==2 and p.shape[1]==6
 fault=1-p[:,0];alarm=fault>alarm_threshold
 conditional=np.divide(p[:,1:],fault[:,None],out=np.zeros_like(p[:,1:]),where=fault[:,None]>0)
 ordered=np.sort(conditional,axis=1);top=np.argmax(conditional,axis=1)
 qualified=(ordered[:,-1]>=confidence)&((ordered[:,-1]-ordered[:,-2])>=margin)
 origin=np.where(alarm&qualified,1<<top,0)
 return alarm,origin
