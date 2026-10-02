#!/usr/bin/env python3
"""Finite attack on exact contextual exchange conditions (post-freeze theorem check)."""
import itertools,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from budget import constrain
from checker import transition
from io_contract import write_json

def main():
 constrain();start=time.process_time();wall=time.perf_counter();cases=0;counts={'12_dominates':0,'21_dominates':0,'incomparable':0}
 for a,b,p,q in itertools.product(range(1,6),repeat=4):
  for z in range(-5,6):
   entry=(max(z,0),max(-z,0));u=transition(entry,(a,b,p,q),0);v=transition(entry,(a,b,p,q),1)
   d12=all(x<=y for x,y in zip(u,v));d21=all(y<=x for x,y in zip(u,v))
   assert u[0]<=v[0] and u[1]>=v[1]
   assert d12==(b>=p and z<=b-a-p)
   assert d21==(a>=q and z>=b+q-a)
   assert not(d12 and d21)
   counts['12_dominates' if d12 else '21_dominates' if d21 else 'incomparable']+=1;cases+=1
 result={'scope':'post-freeze exact exchange theorem finite check, not campaign inclusion', 'cases':cases,'outcomes':counts,
         'search_states':0,'checker_obligations':18*cases,'cpu_seconds':time.process_time()-start,
         'elapsed_wall_seconds':time.perf_counter()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/exchange-conditions.json';write_json(out,result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
