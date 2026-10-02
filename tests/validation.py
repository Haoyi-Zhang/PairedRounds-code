#!/usr/bin/env python3
"""Fixed finite falsification suite. It is not a mechanized general proof."""
import copy,itertools,json,random,resource,sys,time
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from budget import constrain
from model import decode,step
from solver import solve,sort_reference
from checker import check,InvalidCertificate,transition
from oracle import exhaustive,replay
from generation import make,sharp_rows,all_instances
from baselines import heuristic,branch_bound
from io_contract import write_json

def run():
    start=time.process_time();stats={'pair_cases':0,'search_states':0,'checker_obligations':0,'checks':0}
    def must(condition):
        stats['checks']+=1
        if not condition:raise AssertionError('finite check failed')
    def incomparable(s,t):return (s[0]<t[0] and s[1]>t[1]) or (s[0]>t[0] and s[1]<t[1])
    # Ordered input antichains, including different cross-stream offsets.
    for row in itertools.product(range(1,4),repeat=4):
        for dx,dy,offset in itertools.product(range(1,4),range(1,4),range(-3,4)):
            shift=max(0,-offset);s=(shift,shift+offset+dy);t=(shift+dx,shift+offset)
            aa=[step(s,row,b) for b in (0,1)];bb=[step(t,row,b) for b in (0,1)]
            must(not(incomparable(aa[0],bb[0]) and incomparable(aa[1],bb[1])))
            for b in (0,1):
                if incomparable(aa[b],bb[b]):must(aa[b][0]<bb[b][0] and aa[b][1]>bb[b][1])
            stats['pair_cases']+=1;stats['search_states']+=4
    # All depths of the constructive sharp family.
    widths=[]
    for m in range(1,13):
        obj=make('sharp-test',sharp_rows(m),'finite-test');cert=solve(obj);result=check(obj,cert)
        must([len(x['states']) for x in cert['layers']]==list(range(1,m+2)))
        stats['search_states']+=cert['transitions'];stats['checker_obligations']+=result['obligations']
        widths.append(result['max_frontier'])
    # Separate seeded, un-tuned random instances, with full-DAG tiny oracle.
    rng=random.Random(617423);random_cases=56
    for i in range(random_cases):
        m=1+i%7;rows=[tuple(F(rng.randint(1,30),rng.choice((1,2,3,5))) for _ in range(4)) for _ in range(m)]
        obj=make('finite-random',rows,'finite-test');cert=solve(obj);checked=check(obj,cert);oracle=exhaustive(rows)
        front=[tuple(map(F,n['xy'])) for n in cert['layers'][-1]['states']]
        must(front==oracle['frontier']==sort_reference(obj)[0]);must(F(checked['value'])==oracle['value'])
        bb=branch_bound(rows);must(bb['value']==oracle['value'])
        stats['search_states']+=cert['transitions']*2+oracle['tree_states']+bb['tree_states']+bb['initialization_states']
        stats['checker_obligations']+=checked['obligations']
    # All 2^8 interval corners on an explicit two-round graph.
    base=make('corner-test',[(2,3,1,2),(3,1,2,1)],'finite-test',width=F(1,2));hi=decode(base)
    corner_checks=0
    for orders in itertools.product((0,1),repeat=2):
        upper=max(replay(hi,orders));seen=[]
        for corner in itertools.product((0,1),repeat=8):
            vals=[r[j]*(F(1) if corner[4*k+j] else F(1,2)) for k,r in enumerate(hi) for j in range(4)]
            value=max(replay([tuple(vals[:4]),tuple(vals[4:])],orders));must(value<=upper);seen.append(value);corner_checks+=1
        must(max(seen)==upper)
    stats['search_states']+=corner_checks
    # Controlled case showing why a scalar state is invalid.
    rows=[(F(2),F(1),F(1),F(2)),(F(10),F(1),F(1),F(1))]
    neg=make('negative-greedy',rows,'negative-control');cert=solve(neg);checked=check(neg,cert)
    greedy=heuristic(rows,'greedy-makespan')[0];must(F(checked['value'])==14 and greedy==15)
    stats['search_states']+=cert['transitions']+6;stats['checker_obligations']+=checked['obligations']
    # Correlation changes the admissible uncertainty set: upper box corner is infeasible.
    correlated=max(max(replay([(F(1),F(1),F(p),F(3-p))],[0])) for p in (1,2))
    box=max(replay([(F(1),F(1),F(2),F(2))],[0]));must(correlated==4 and box==5)
    stats['search_states']+=3
    # Generic 2x2 max-plus diagonal maps need not have linear width.
    front={(0,0)}
    for k in range(12):
        stats['search_states']+=2*len(front)
        front={(x+2**k,y) for x,y in front}|{(x,y+2**k) for x,y in front}
    must(len(front)==4096 and len({x+y for x,y in front})==1)
    # Lower-endpoint sensitivity with upper endpoints held fixed.
    sensitive=0
    for obj in all_instances():
        original=solve(obj);stats['search_states']+=original['transitions']
        for width in (F(0),F(1,4),F(1,2),F(3,4)):
            altered=copy.deepcopy(obj)
            for row in altered['stages']:
                for v in row.values():v['lo']=str(F(v['hi'])*(1-width))
            c=solve(altered);r=check(altered,c)
            must(c['upper_bound']==original['upper_bound']);must(c['orders']==original['orders'])
            stats['search_states']+=c['transitions'];stats['checker_obligations']+=r['obligations'];sensitive+=1
    # Certificate mutation classes: all should be cleanly rejected, never accepted.
    obj=neg;valid=solve(obj);mutations=[]
    def add(name,change,changeinput=False):
        o,c=copy.deepcopy(obj),copy.deepcopy(valid)
        change(o if changeinput else c);mutations.append((name,o,c))
    add('missing-layer',lambda c:c['layers'].pop())
    add('unreachable-coordinate',lambda c:c['layers'][1]['states'][0]['xy'].__setitem__(0,'0'))
    add('missing-branch',lambda c:c['layers'][1]['cover'][0].pop())
    add('invalid-dominator',lambda c:c['layers'][1]['cover'][0].__setitem__(0,100))
    add('invalid-parent',lambda c:c['layers'][1]['states'][0].__setitem__('parent',100))
    add('nonbinary-order',lambda c:c['layers'][1]['states'][0].__setitem__('order',2))
    add('boolean-order',lambda c:c['layers'][1]['states'][0].__setitem__('order',True))
    add('false-lower-bound',lambda c:c.__setitem__('lower_bound','13'))
    add('false-upper-bound',lambda c:c.__setitem__('upper_bound','15'))
    add('wrong-incumbent',lambda c:c.__setitem__('orders',[1,0]))
    add('malformed-layer',lambda c:c['layers'].__setitem__(1,[]))
    add('duplicate-frontier-node',lambda c:c['layers'][1]['states'].append(c['layers'][1]['states'][0]))
    add('unsupported-constraint',lambda o:o.__setitem__('extra_edges',[[0,1]]),True)
    add('third-compute-resource',lambda o:o['resources'].insert(2,'C3'),True)
    add('invalid-interval',lambda o:o['stages'][0]['p1'].__setitem__('lo','100'),True)
    add('endpoint-width',lambda o:o['stages'][0]['p1'].__setitem__('hi',str(2**64)),True)
    add('oversized-rational',lambda c:c.__setitem__('lower_bound','1'*2300))
    add('identity-mismatch',lambda c:c.__setitem__('instance_id','another-case'))
    mutation_results=[]
    for name,o,c in mutations:
        try:check(o,c)
        except InvalidCertificate:mutation_results.append({'name':name,'rejected':True})
        else:raise AssertionError('accepted mutation: '+name)
        # Conservative charge the complete valid certificate, since failure can happen early.
        stats['checker_obligations']+=checked['obligations'];stats['checks']+=1
    return dict(stats,sharp_widths=widths,random_cases=random_cases,corner_checks=corner_checks,
                interval_sensitivity_cases=sensitive,mutation_results=mutation_results,
                greedy_negative={'exact':'14','greedy':'15'},correlation_negative={'actual':'4','box':'5'},
                generic_diagonal_width=4096,cpu_seconds=time.process_time()-start,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,workers=1)

if __name__=='__main__':
    constrain();result=run();out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results'/'validation.json'
    write_json(out,result);print(json.dumps({k:v for k,v in result.items() if k not in ('mutation_results',)},sort_keys=True))
