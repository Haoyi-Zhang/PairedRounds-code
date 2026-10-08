"""Exact equivalence of compiled and dynamic local graphs, including rejection."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tests'))
import checker
from dag_reference import checker_module,transition
from io_contract import read_json

class GraphTopologyTests(unittest.TestCase):
    def test_local_rational_grid_and_strict_orders(self):
        count=0
        for entry in product((F(0),F(1,2),F(1),F(5,3),F(3)),repeat=2):
            for durations in product((F(1,3),F(1),F(2),F(5,2)),repeat=4):
                for order in (0,1):
                    self.assertEqual(checker.transition(entry,durations,order),transition(entry,durations,order))
                    count+=1
        self.assertEqual(count,12800)
        for order in (False,True,1.0,'0',None,-1,2):
            for evaluate in (checker.transition,transition):
                with self.assertRaisesRegex(ValueError,'nonbinary order'):
                    evaluate((F(0),F(0)),(F(1),)*4,order)

    def test_all_frozen_certificates_and_invalid_mutations(self):
        reference=checker_module()
        count=0;rejections=0
        for path in sorted((ROOT/'inputs').glob('*.json')):
            obj=read_json(path)
            cert=read_json(ROOT/'results/host-campaign/certificates'/path.name)
            frozen=read_json(ROOT/'results/host-campaign/cases'/path.name)['checker']
            self.assertEqual(checker.check(obj,cert),frozen)
            self.assertEqual(reference.check(obj,cert),frozen)
            count+=1
            mutations=[]
            for field,value in [('instance_id','other-input'),('lower_bound','-1'),('upper_bound','-1'),('terminal',True),('transitions',-1)]:
                bad=deepcopy(cert);bad[field]=value;mutations.append((obj,bad))
            for field,value in [('parent',True),('parent',-1),('order',True),('order',1.0),('xy',['-1','0'])]:
                bad=deepcopy(cert);bad['layers'][1]['states'][0][field]=value;mutations.append((obj,bad))
            bad=deepcopy(cert);bad['layers'][1]['cover'][0][0]=True;mutations.append((obj,bad))
            bad=deepcopy(cert);bad['layers'][1]['cover'][0]=[];mutations.append((obj,bad))
            bad=deepcopy(cert);bad['orders'][0]=True;mutations.append((obj,bad))
            bad=deepcopy(obj);bad['stages'][0]['p1']['hi']='0';mutations.append((bad,cert))
            bad=deepcopy(obj);bad['resources'].append('L2');mutations.append((bad,cert))
            for changed_obj,changed_cert in mutations:
                messages=[]
                for module in (checker,reference):
                    with self.assertRaises(ValueError) as raised:
                        module.check(changed_obj,changed_cert)
                    messages.append(str(raised.exception))
                self.assertEqual(*messages);rejections+=1
            # No reuse across input mutations or complete checker invocations.
            self.assertEqual(checker.check(obj,cert),frozen)
        self.assertEqual(count,36)
        self.assertEqual(rejections,540)

if __name__=='__main__':
    unittest.main()
