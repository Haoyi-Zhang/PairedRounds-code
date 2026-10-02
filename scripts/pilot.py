import argparse,sys,json,time,resource
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from budget import constrain
constrain()
from generation import make,sharp_rows
from solver import solve,sort_reference
from checker import check
from oracle import exhaustive
from model import decode
from baselines import heuristic,branch_bound
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Repeat the intake pilot without overwriting retained evidence.')
parser.add_argument('--output',type=Path,default=Path('results/pilot.json'))
args=parser.parse_args()
t=time.process_time();out=[]
for obj in [make('pilot-sharp',sharp_rows(12),'pilot'),make('pilot-negative',[(2,1,1,2),(10,1,1,1)],'pilot')]:
    cert=solve(obj);checked=check(obj,cert);ref=exhaustive(decode(obj));assert checked['value']==str(ref['value'])
    assert [tuple(map(str,s)) for s in ref['frontier']]==[tuple(s['xy']) for s in cert['layers'][-1]['states']]
    value,orders,cost=heuristic(decode(obj),'greedy-makespan');bb=branch_bound(decode(obj));assert bb['value']==ref['value']
    out.append({'input':obj,'certificate':cert,'check':checked,'oracle_value':str(ref['value']),'oracle_tree_states':ref['tree_states'],'oracle_event_evaluations':ref['event_evaluations'],'greedy_value':str(value),'greedy_states':cost,'bb_states':bb['tree_states']})
report={'runs':out,'cpu_seconds':time.process_time()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
output=args.output if args.output.is_absolute() else root/args.output
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2));print([(x['input']['id'],x['check']['max_frontier'],x['check']['value'],x['greedy_value']) for x in out])
