#!/usr/bin/env python3
import collections
import copy
import itertools
import json
import unittest
import reference_oracle as m

class OracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds={c:[m.execute(r,c) for r in m.realizations()] for c in m.CONTEXTS}
    def test_domain_exhaustive_counts(self):
        counts=collections.Counter(r['origin'] for r in m.realizations())
        self.assertEqual(dict(counts),dict(healthy=1,memory=24,timing=10,communication=12,sensor=12,actuator=8))
        self.assertEqual(len({r['id'] for r in m.realizations()}),67)
    def test_index_against_independent_linear_reference(self):
        for es in self.worlds.values():
            for p in m.POLICIES:
                for t in m.TIMES:
                    ix=m.compatibility_index(es,p,t)
                    for h,executions in ix.items():
                        origins=m.brute_compatible(h,es,p,t)
                        self.assertEqual(origins,{e['realization']['origin'] for e in executions})
                        self.assertEqual(m.decide(h,ix),next(iter(origins)) if len(origins)==1 else 'UNKNOWN')
    def test_all_execution_prefixes_sound(self):
        for es in self.worlds.values():
            for p in m.POLICIES:
                for t in m.TIMES:
                    ix=m.compatibility_index(es,p,t)
                    for e in es:
                        answer=m.decide(m.history(e,p,t),ix)
                        self.assertIn(answer,('UNKNOWN',e['realization']['origin']))
    def test_unknown_for_unmodeled_history(self):
        self.assertEqual(m.decide((('not-an-observation',),),{}),'UNKNOWN')
    def test_projection_no_oracle_fields(self):
        forbidden={'origin','kind','parameter','configured_active','coolant_true_c','reference_coolant_true_c',
                   'diagnostic_id','safety_state','detector_alarm','fault_active','memory_original_value'}
        for fields,_ in m.POLICIES.values(): self.assertFalse(set(fields)&forbidden)
        e=copy.deepcopy(self.worlds['zero_command'][1]); before=m.history(e,'full_100',400)
        e['realization']={'origin':'fake','parameter':1234};e['model_events_not_checker_input']=[]
        self.assertEqual(before,m.history(e,'full_100',400))
    def test_exact_one_bit_numeric_difference(self):
        e=copy.deepcopy(self.worlds['zero_command'][0]);other=copy.deepcopy(e)
        other['observations'][1]['pump_actual']='00000001'
        self.assertNotEqual(m.history(e,'values_100',400),m.history(other,'values_100',400))
    def test_finer_policy_cannot_add_competitors(self):
        es=self.worlds['positive_command']
        for e in es:
            full=m.brute_compatible(m.history(e,'full_100',400),es,'full_100',400)
            for p in ('timestamp_100','values_100','full_200'):
                self.assertLessEqual(full,m.brute_compatible(m.history(e,p,400),es,p,400))
    def test_longer_history_cannot_add_competitors(self):
        for es in self.worlds.values():
            for p in m.POLICIES:
                for e in es:
                    previous=set(m.ORIGINS)|{'healthy'}
                    for t in m.TIMES:
                        current=m.brute_compatible(m.history(e,p,t),es,p,t)
                        self.assertLessEqual(current,previous);previous=current
    def test_replay_all_saved_ambiguities(self):
        report=json.loads((m.HERE/'competing_fault_worlds.json').read_text())
        for c in report['ambiguities']:
            a=m.execute(c['world_a'],c['context']);b=m.execute(c['world_b'],c['context'])
            h=m.history(a,c['policy'],c['deadline_ms'])
            self.assertNotEqual(c['world_a']['origin'],c['world_b']['origin'])
            self.assertEqual(h,m.history(b,c['policy'],c['deadline_ms']))
            self.assertEqual(json.loads(json.dumps(h)),c['runtime_history'])
    def test_pair_results_independent_cross_product(self):
        report=json.loads((m.HERE/'competing_fault_worlds.json').read_text())
        self.assertEqual(len(report['pair_results']),240)
        for p in report['pair_results']:
            es=self.worlds[p['context']];a=[e for e in es if e['realization']['origin']==p['origin_a']]
            b=[e for e in es if e['realization']['origin']==p['origin_b']]
            # Explicit row lists, independent of indexed pair lookup.
            fields,period=m.POLICIES[p['policy']]
            def rows(e):return [[r['time_ms']]+[r[f] for f in fields] for r in e['observations'] if r['time_ms']<=p['deadline_ms'] and r['time_ms']%period==0]
            overlap=any(rows(x)==rows(y) for x,y in itertools.product(a,b))
            self.assertEqual(p['result']=='INDISTINGUISHABLE',overlap)
            if overlap:
                c=p['counterexample'];self.assertEqual(rows(m.execute(c['world_a'],p['context'])),c['runtime_history'])
                self.assertEqual(rows(m.execute(c['world_b'],p['context'])),c['runtime_history'])
    def test_pulse_acquisition_alignment(self):
        rs=[r for r in m.realizations() if r['kind']=='bias' and r['duration']==25]
        healthy=self.worlds['positive_command'][0]
        for r in rs:
            eq=m.history(m.execute(r,'positive_command'),'full_100',400)==m.history(healthy,'full_100',400)
            self.assertEqual(eq,r['start']==150)
    def test_pump_zero_and_positive_excitation(self):
        r=next(r for r in m.realizations() if r['kind']=='pump' and r['parameter']==.5)
        for c in m.CONTEXTS:
            a=m.execute(r,c);b=self.worlds[c][0]
            self.assertEqual(m.history(a,'full_100',400)==m.history(b,'full_100',400),c=='zero_command')
    def test_memory_restore_and_matching_stuck(self):
        for r in m.realizations():
            if r['origin']!='memory':continue
            e=m.execute(r,'positive_command')
            self.assertEqual(e['observations'][-1]['target_register_c'],92)
            if r['kind']=='stuck' and r['aux']==((92>>r['parameter'])&1):
                self.assertEqual(m.history(e,'full_100',400),m.history(self.worlds['positive_command'][0],'full_100',400))
    def test_pending_delay_survives_recovery(self):
        r=next(r for r in m.realizations() if r['kind']=='delay' and r['start']==100 and r['duration']==100 and r['parameter']==200)
        e=m.execute(r,'positive_command')
        self.assertEqual([o['control_execution_ms'] for o in e['observations']],[0,0,0,300,400])
    def test_full_c_component_comparison(self):
        report=json.loads((m.HERE/'ecu_comparison.json').read_text())
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['discrepancies'],[])
        self.assertEqual(report['rows_compared'],670)
        rows=json.loads((m.HERE/'actual_component_observations.json').read_text())
        for c in rows:
            r=next(r for r in m.realizations() if r['id']==c['realization_id'])
            self.assertEqual(c['observations'],m.execute(r,c['context'])['observations'])
    def test_preserved_findings_and_source_anchors(self):
        report=json.loads((m.HERE/'v6_import_verification.json').read_text())
        self.assertEqual(len(report['preserved_unresolved_findings']),41)
        self.assertEqual(report['anchor_errors'],[])
        model=json.loads((m.HERE/'two_world_model.json').read_text())
        root=m.HERE.parents[1]
        for a in model['source_anchors']:
            self.assertIn(a['token'],(root/a['path']).read_text().splitlines()[a['line']-1])
    def test_saved_frontier_independent_recount(self):
        import csv
        rows=list(csv.DictReader((m.HERE/'diagnosability_frontier.csv').open()))
        self.assertEqual(len(rows),24)
        for row in rows:
            es=self.worlds[row['context']]; p=row['policy']; t=int(row['deadline_ms'])
            histories={m.history(e,p,t) for e in es}
            ambiguous=[h for h in histories if len(m.brute_compatible(h,es,p,t))>1]
            self.assertEqual(int(row['histories']),len(histories))
            self.assertEqual(int(row['ambiguous_histories']),len(ambiguous))
            self.assertEqual(int(row['unique_origin_histories']),len(histories)-len(ambiguous))
            self.assertEqual(int(row['unknown_executions']),sum(m.history(e,p,t) in ambiguous for e in es))
    def test_saved_positive_earliest_times(self):
        positives=json.loads((m.HERE/'conditional_positive_histories.json').read_text())
        for p in positives:
            h=tuple(tuple(r) for r in p['runtime_history']); es=self.worlds[p['context']]
            self.assertEqual(m.brute_compatible(h,es,p['policy'],p['deadline_ms']),{p['origin']})
            for t in m.TIMES:
                if t>p['deadline_ms']:continue
                prefix=tuple(r for r in h if r[0]<=t)
                singleton=len(m.brute_compatible(prefix,es,p['policy'],t))==1
                self.assertEqual(singleton,t>=p['earliest_unique_ms'])
    def test_model_spec_matches_executable_domain(self):
        spec=json.loads((m.HERE/'two_world_model.json').read_text())
        self.assertEqual(spec['realizations'],m.realizations())
        self.assertEqual(spec['policies'],{p:{'fields':list(f),'capture_period_ms':t,'assumptions':m.POLICY_ASSUMPTIONS[p]} for p,(f,t) in m.POLICIES.items()})

if __name__=='__main__': unittest.main(verbosity=2)
