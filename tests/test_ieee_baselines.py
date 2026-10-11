import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from virtual_ecu.ieee_baselines import ewma,cusum,detect_edges

class IEEEBackendTests(unittest.TestCase):
    def test_ewma_causal_and_decay(self):
        x=np.array([[0],[1],[0],[0]],float)
        np.testing.assert_allclose(ewma(x,.5),[0,.5,.25,.125])
        np.testing.assert_equal(ewma(x,.5)[:2],ewma(x[:2],.5))
    def test_cusum_matches_recurrence(self):
        x=np.random.default_rng(42).uniform(0,1,(200,6));s=np.zeros(6);expected=[]
        for row in x:
            s=np.maximum(0,s+row-.4);expected.append(s.max())
        np.testing.assert_allclose(cusum(x,.4),expected,atol=1e-12)
    def test_no_future_information_or_state_leak(self):
        x=np.r_[np.zeros(5),np.ones(5)][:,None]
        np.testing.assert_equal(cusum(x,.1)[:5],np.zeros(5))
        np.testing.assert_equal(cusum(np.zeros((8,6)),.1),np.zeros(8))
    def test_edge_accounting(self):
        self.assertEqual(detect_edges([1,1,1],.5,[0,100,200],100),(False,True))
        self.assertEqual(detect_edges([0,0,1],.5,[0,100,200],100),(True,True))
        self.assertEqual(detect_edges([.5,.5],.5,[0,100],0),(False,False))

if __name__=='__main__':unittest.main()
