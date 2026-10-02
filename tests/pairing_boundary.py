#!/usr/bin/env python3
"""Post-freeze boundary control; not a newly included campaign instance."""
import itertools,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from budget import constrain
from generation import make
from solver import solve
from checker import check
from io_contract import write_json

def main():
 constrain();begin=time.process_time()
 # Tuple rows use the declared (compute 1, compute 2, transfer 1, transfer 2) order.
 rows=[(1,10,1,1),(1,1,5,1)]
 obj=make('pairing-boundary',rows,'post-freeze-boundary')
 out=[]
 for positions in itertools.combinations(range(4),2):
  word=[1 if i in positions else 2 for i in range(4)]
  # Independent general-link replay: own computation starts after own preceding T.
  # Link word respects the order of each chain but not paired rounds.
  own=[0,0];used=[0,0];link=0;trace=[]
  for who in word:
   i=who-1;k=used[i];a,b,p,q=rows[k]
   compute=(a,b)[i];transfer=(p,q)[i]
   ready=own[i]+compute;start=max(link,ready);end=start+transfer
   trace.append({'stream':who,'round':k+1,'compute_start':own[i], 'compute_end':ready,'transfer_start':start,'transfer_end':end})
   own[i]=end;link=end;used[i]+=1
  paired=all(sorted(word[k:k+2])==[1,2] for k in (0,2))
  out.append({'word':word,'paired':paired,'makespan':max(own),'trace':trace})
 cert=solve(obj);checked=check(obj,cert)
 assert min(r['makespan'] for r in out)==13
 assert min(r['makespan'] for r in out if r['paired'])==17
 assert checked['value']=='17'
 result={'scope':'post-freeze boundary illustration, not campaign inclusion', 'input':obj, 'orders':out,
         'unrestricted_optimum':'13','paired_optimum':'17','certificate':cert,'check':checked,
         'search_states':6+cert['transitions'],'checker_obligations':checked['obligations'],
         'cpu_seconds':time.process_time()-begin,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
 path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/pairing-boundary.json'
 write_json(path,result);print(json.dumps({k:result[k] for k in ('paired_optimum','unrestricted_optimum','search_states','checker_obligations','cpu_seconds')},sort_keys=True))
if __name__=='__main__':main()
