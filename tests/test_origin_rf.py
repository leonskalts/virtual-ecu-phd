import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu import origin_rf as r,comparative_backends as b
class OriginRFTests(unittest.TestCase):
 def test_ambiguity_abstains_without_suppressing_alarm(self):
  a,o=r.decisions(np.array([[.1,.45,.45,0,0,0],[.1,0,0,0,.9,0],[1,0,0,0,0,0]]),.5,.8,.1)
  self.assertEqual(a.tolist(),[True,True,False]);self.assertEqual(o.tolist(),[0,8,0])
 def test_normal_and_fault_threshold_are_separate(self):
  a,o=r.decisions(np.array([[.6,.4,0,0,0,0]]),.3,.9,.1)
  self.assertEqual((bool(a[0]),int(o[0])),(True,1))
 def test_feature_causality_and_clock_translation(self):
  n=80;p=np.ones((n,len(r.FIELDS)));p[:,0]=np.arange(n)*100
  for name in r.TIME_FIELDS:p[:,r.FIELDS.index(name)]=p[:,0]-5
  e=b.Evidence(p[:,0],np.random.default_rng(4).random((n,6)),np.ones((n,6),bool),np.tile([2,4,1,8,16,31],(n,1)))
  x=r.features(p,e);short=b.Evidence(e.time_ms[:20],e.strength[:20],e.available[:20],e.origin_subset[:20])
  np.testing.assert_equal(x[:20],r.features(p[:20],short))
  q=p.copy();q[:,0]+=10000
  # Keep negative timestamp sentinels unchanged; positive timestamps translate.
  for name in r.TIME_FIELDS:
   j=r.FIELDS.index(name);q[:,j]=np.where(p[:,j]>=0,p[:,j]+10000,p[:,j])
  np.testing.assert_equal(x,r.features(q,b.Evidence(e.time_ms+10000,e.strength,e.available,e.origin_subset)))
 def test_schema_excludes_diagnostic_answers(self):
  self.assertNotIn('detector_alarm',r.FIELDS);self.assertNotIn('direct_origins',r.FIELDS)
if __name__=='__main__':unittest.main()
