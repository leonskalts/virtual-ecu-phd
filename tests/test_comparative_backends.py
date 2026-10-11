"""Synthetic evidence contracts: missingness, ambiguity and classical fusion."""
import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu import comparative_backends as b

class ComparativeBackendTests(unittest.TestCase):
 def evidence(self,values,available=None,subsets=None):
  v=np.array(values,float).reshape(-1,6);n=len(v)
  return b.Evidence(np.arange(n)*100,v,np.ones_like(v,bool) if available is None else np.asarray(available,bool).reshape(n,6),np.tile([2,4,1,8,16,31],(n,1)) if subsets is None else np.asarray(subsets).reshape(n,6))
 def test_unavailable_is_not_a_healthy_denominator(self):
  e=self.evidence([0,0,0,.6,0,0],[0,0,0,1,0,0])
  self.assertTrue(b.weighted_sum(e,[1]*6,.5)[0][0])
  self.assertEqual(e.features[0,9],1)
  self.assertFalse(b.weighted_sum(self.evidence([0,0,0,.6,0,0]),[1]*6,.5)[0][0])
 def test_or_ambiguity(self):
  e=self.evidence([[1,0,0,0,0,0],[1,0,0,1,0,0],[0,0,0,0,0,1]])
  alarm,origin=b.simple_or(e)
  self.assertEqual(alarm.tolist(),[True]*3);self.assertEqual(origin.tolist(),[2,0,0])
 def test_classical_conjunctive_fusion(self):
  e=self.evidence([[.3,0,0,.3,0,0],[0,0,0,1,0,0],[1,1,0,0,0,0],[0]*6])
  a,o=b.plain_ds(e)
  self.assertEqual(a.tolist(),[True,True,True,False])
  self.assertEqual(o.tolist(),[0,8,0,0])
 def test_imprecise_origin_is_not_forced(self):
  e=self.evidence([0,0,0,1,0,0],subsets=[2,4,1,12,16,31])
  self.assertEqual(b.simple_or(e)[1][0],0)
  self.assertEqual(b.plain_ds(e)[1][0],0)
 def test_features_cannot_expose_time_or_origin(self):
  e=self.evidence([[.2,0,0,0,0,0]]*2)
  np.testing.assert_equal(e.features[0],e.features[1])
  self.assertEqual(e.features.shape,(2,12))

if __name__=='__main__':unittest.main()
