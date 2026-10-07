"""Finite exact checker transition reuse; separate public regression step."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import checker
from generation import make,sharp_rows
from oracle import exhaustive
from solver import solve


def owned_cases():
    for values in product((F(1,2),F(2)),repeat=4):
        for depth in (1,2,3):
            rows=[values if k%2==0 else tuple(reversed(values)) for k in range(depth)]
            yield make('owned-cache',rows,'owned-finite',width=F(1))


class TransitionCacheTests(unittest.TestCase):
    def test_full_event_oracle_and_unchanged_semantic_obligations(self):
        for obj in owned_cases():
            snapshot=deepcopy(obj)
            cert=solve(obj)
            rows=checker.input_rows(obj)
            defined=exhaustive(rows)
            got=checker.check(obj,cert)
            self.assertEqual(F(got['value']),defined['value'])
            self.assertEqual([tuple(map(F,n['xy'])) for n in cert['layers'][-1]['states']],defined['frontier'])
            retained=sum(len(l['states']) for l in cert['layers'][1:])
            self.assertEqual(got['obligations'],1+9*retained+11*cert['transitions']+9*len(rows))
            self.assertEqual(got['transitions'],cert['transitions'])
            self.assertEqual(obj,snapshot)

    def test_strict_orders_before_numeric_cache_hits_and_other_rejections(self):
        obj=make('owned-invalid',sharp_rows(2),'owned-finite')
        cert=solve(obj)
        for order in (False,True,'0',1.0,None,2):
            damaged=deepcopy(cert)
            # For bool/float, prime the equal-valued valid numeric cache key
            # before the invalid second row. No input/type gate is weakened.
            first=next(n for n in cert['layers'][1]['states'] if n['order']==int(order or 0)) if order in (False,True,1.0) else cert['layers'][1]['states'][0]
            damaged['layers'][1]['states']=[deepcopy(first),deepcopy(first)]
            damaged['layers'][1]['states'][1]['order']=order
            with self.assertRaisesRegex(checker.InvalidCertificate,'nonbinary order'):
                checker.check(obj,damaged)
        for parent in (False,True,'0',-1,100):
            damaged=deepcopy(cert);damaged['layers'][1]['states'][0]['parent']=parent
            with self.assertRaisesRegex(checker.InvalidCertificate,'bad parent'):
                checker.check(obj,damaged)
        damaged=deepcopy(cert);damaged['layers'][1]['cover'][0][0]=100
        with self.assertRaisesRegex(checker.InvalidCertificate,'invalid dominator'):
            checker.check(obj,damaged)
        damaged=deepcopy(cert);damaged['orders'][0]=True
        with self.assertRaisesRegex(checker.InvalidCertificate,'nonbinary order'):
            checker.check(obj,damaged)

    def test_layer_only_evaluator_calls_and_fresh_input_validation(self):
        obj=make('owned-sharp',sharp_rows(6),'owned-finite')
        cert=solve(obj)
        with patch.object(checker,'transition',wraps=checker.transition) as invoked:
            result=checker.check(obj,cert)
        self.assertEqual(invoked.call_count,cert['transitions']+len(obj['stages']))
        self.assertEqual(result['nodes'],sum(len(l['states']) for l in cert['layers']))
        bad=deepcopy(obj);bad['stages'][-1]['p2']['hi']='0'
        with self.assertRaisesRegex(checker.InvalidCertificate,'invalid duration'):
            checker.check(bad,cert)
        self.assertEqual(checker.check(obj,cert),result)


if __name__=='__main__':
    unittest.main()
