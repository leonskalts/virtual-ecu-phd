#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
import importlib.util
import itertools
import json
import unittest
import compare_methods as m

class ReductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=m.load_cases()
        cls.results=json.loads((m.HERE/'comparison_results.json').read_text())
    def test_common_feasible_regions_and_joint_optima(self):
        for case in self.cases:
            rs=[r for r in self.results if r['case']==case['name']]
            self.assertEqual(len(rs),4)
            for r in rs[1:]:
                for key in ('feasible','costs','best_objective','best_contracts','reference_decisions'):
                    self.assertEqual(r[key],rs[0][key],(case['name'],r['method'],key))
    def test_exact_clause_equivalence_all_contracts(self):
        for case in self.cases:
            labs=m.labels(case);k=len(case['bundles'])
            target=m.partition_decisions(m.histories(case,(1<<k)-1,100),labs);req=m.required_pairs(target,labs)
            for period in case['periods']:
                clauses=set(m.diff_mask(case,i,j,period) for i,j in req)
                for mask in range(1<<k):
                    actual=m.partition_decisions(m.histories(case,mask,period),labs)
                    self.assertEqual(actual==target,all(mask&c for c in clauses),(case['name'],period,mask))
    def test_sound_source_support_all_world_pairs(self):
        for case in self.cases[:6]:
            for period in case['periods']:
                for i,j in itertools.combinations(range(len(case['worlds'])),2):
                    exact=m.diff_mask(case,i,j,period);support=m.support_mask(case,i,j,period)
                    self.assertEqual(exact&~support,0,(case['name'],i,j,period))
    def test_support_rejection_has_real_counterexample(self):
        for case in self.cases[:6]:
            labs=m.labels(case);k=len(case['bundles']);target=m.partition_decisions(m.histories(case,(1<<k)-1,100),labs)
            req=m.required_pairs(target,labs)
            for period in case['periods']:
                clauses=m.reduced_clauses(m.support_mask(case,i,j,period) for i,j in req)
                for mask in range(1<<k):
                    if not all(mask&c for c in clauses):
                        self.assertNotEqual(m.partition_decisions(m.histories(case,mask,period),labs),target)
    def test_support_is_not_sufficient(self):
        case=self.cases[2];ws=case['worlds']
        a=next(i for i,w in enumerate(ws) if w['realization']['kind']=='stuck' and w['realization']['parameter']==0 and w['realization']['aux']==0)
        b=next(i for i,w in enumerate(ws) if w['realization']['kind']=='pump')
        self.assertNotEqual(m.support_mask(case,a,b,100),0)
        self.assertEqual(m.diff_mask(case,a,b,100),0)
    def test_underestimated_support_is_invalid(self):
        case=self.cases[5];ws=case['worlds']
        a=0;b=next(i for i,w in enumerate(ws) if w['realization']['kind']=='flip')
        self.assertNotEqual(m.diff_mask(case,a,b,100),0)
        bad_upper_bound=0
        self.assertNotEqual(m.diff_mask(case,a,b,100)&~bad_upper_bound,0)
    def test_minimized_checker_all_prefixes(self):
        for case in self.cases:
            labs=m.labels(case)
            for period in case['periods']:
                for mask in range(1<<len(case['bundles'])):
                    hs=m.histories(case,mask,period);machine=m.checker(hs,labs)
                    for length in range(len(hs[0])+1):
                        prefixes=[h[:length] for h in hs]
                        expected=m.partition_decisions(prefixes,labs)
                        self.assertEqual([m.run_checker(machine,h) for h in prefixes],expected)
                    self.assertEqual(m.run_checker(machine,((99999,'unsupported'),)),'UNKNOWN')
    def test_unknown_and_origin_soundness(self):
        for case in self.cases:
            labs=m.labels(case);full=m.partition_decisions(m.histories(case,(1<<len(case['bundles']))-1,100),labs)
            for p in case['periods']:
                for mask in range(1<<len(case['bundles'])):
                    decisions=m.partition_decisions(m.histories(case,mask,p),labs)
                    for i,d in enumerate(decisions):
                        self.assertIn(d,('UNKNOWN',labs[i]))
                        if full[i]=='UNKNOWN':self.assertEqual(d,'UNKNOWN')
    def test_positive_clause_subsumption(self):
        clauses=[0b11,0b111,0b101,0b11]
        reduced=m.reduced_clauses(clauses)
        for mask in range(8):self.assertEqual(all(mask&c for c in clauses),all(mask&c for c in reduced))
        self.assertEqual(m.reduced_clauses([0,1,2]),[0])
    def test_no_truth_metadata_in_contracts(self):
        spec=json.loads((m.ROOT/'research/clover_cert_v7/two_world_model.json').read_text())
        allowed=set(spec['policies']['full_100']['fields'])
        self.assertEqual({f for b in m.BUNDLES for f in b},allowed)
        self.assertNotIn('origin',allowed);self.assertNotIn('configured_active',allowed)
    def test_imported_v7_reference_exact_decisions(self):
        path=m.ROOT/'research/clover_cert_v7/reference_oracle.py'
        spec=importlib.util.spec_from_file_location('v7_readonly',path);v7=importlib.util.module_from_spec(spec);spec.loader.exec_module(v7)
        for case in self.cases[:6]:
            index=v7.compatibility_index(case['worlds'],'full_100',case['deadline'])
            expected=[v7.decide(v7.history(w,'full_100',case['deadline']),index) for w in case['worlds']]
            self.assertEqual(expected,m.partition_decisions(m.histories(case,31,100),m.labels(case)))
    def test_all_unresolved_findings_preserved(self):
        imported=json.loads((m.HERE/'research_import.json').read_text())
        old=json.loads((m.ROOT/'research/clover_cert_v6_audit/validation_report.json').read_text())
        self.assertEqual(imported['unresolved_findings'],old['unresolved_findings'])
        self.assertEqual(len(imported['unresolved_findings']),41)
        self.assertEqual(imported['anchor_errors'],[])

if __name__=='__main__':unittest.main(verbosity=2)
