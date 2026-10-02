#!/usr/bin/env python3
"""Run the frozen 36-case campaign; each output is a resumable case chunk.

Every method uses the same positive upper-endpoint instance on one CPU worker.
No device performance is measured. Re-running to another --output retains both
measurements for honest clean-extraction reproduction.
"""
import argparse,csv,json,resource,statistics,sys,time
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from budget import constrain
from io_contract import read_json,write_json
from generation import all_instances
from model import decode
from solver import solve,sort_reference
from checker import check
from oracle import exhaustive
from baselines import heuristic,branch_bound

KINDS=('fixed12','fixed21','earliest-release','bottom-level','greedy-makespan')
REPEATS=5

def timed(f,repeats):
    samples=[];values=[]
    for _ in range(repeats):
        begin=time.perf_counter_ns();v=f();elapsed=time.perf_counter_ns()-begin
        values.append(v);samples.append(elapsed)
    return values,samples

def case(obj):
    rows=decode(obj);start=time.process_time();raw={};counts={'search_states':0,'checker_obligations':0}
    certs,t=timed(lambda:solve(obj),REPEATS);cert=certs[0]
    if not all(c==cert for c in certs):raise AssertionError('nondeterministic solver result')
    raw['merge']=t;counts['search_states']+=REPEATS*cert['transitions']
    checks,t=timed(lambda:check(obj,cert),REPEATS);checked=checks[0];raw['checker']=t
    counts['checker_obligations']+=REPEATS*checked['obligations']
    ref,t=timed(lambda:sort_reference(obj),REPEATS);raw['sort']=t
    counts['search_states']+=sum(c[1] for c in ref)
    oracle,t=timed(lambda:exhaustive(rows),1);oracle=oracle[0];raw['oracle']=t
    counts['search_states']+=oracle['tree_states']
    frontier=[tuple(map(F,n['xy'])) for n in cert['layers'][-1]['states']]
    if not (frontier==oracle['frontier']==ref[0][0] and F(cert['upper_bound'])==oracle['value']):
        raise AssertionError('whole-frontier oracle mismatch')
    bbs,t=timed(lambda:branch_bound(rows),REPEATS);bb=bbs[0];raw['branch-bound']=t
    counts['search_states']+=sum(b['tree_states']+b['initialization_states'] for b in bbs)
    if bb['value']!=oracle['value']:raise AssertionError('branch-bound oracle mismatch')
    heuristic_results={}
    for kind in KINDS:
        values,t=timed(lambda:heuristic(rows,kind),REPEATS);raw[kind]=t
        value,orders,states=values[0];counts['search_states']+=sum(v[2] for v in values)
        if value<oracle['value']:raise AssertionError('invalid heuristic bound')
        heuristic_results[kind]={'value':str(value),'orders':orders,'states':states,
            'relative_gap':str((value-oracle['value'])/oracle['value'])}
    widths=[len(x['states']) for x in cert['layers']]
    state_bits=max(max(abs(F(z).numerator).bit_length(),F(z).denominator.bit_length()) for layer in cert['layers'] for node in layer['states'] for z in node['xy'])
    endpoint_bits=max(max(abs(F(v[e]).numerator).bit_length(),F(v[e]).denominator.bit_length()) for row in obj['stages'] for v in row.values() for e in ('lo','hi'))
    evidence={'id':obj['id'],'group':obj['group'],'source_schema':obj['source_schema'],
        'rounds':len(rows),'events':4*len(rows),'edge_bound':6*len(rows)-3,
        'value':cert['upper_bound'],'terminal_frontier':[[str(z) for z in p] for p in frontier],
        'widths':widths,'checker':checked,'certificate_bytes':len((json.dumps(cert,indent=2,sort_keys=True)+'\n').encode()),
        'endpoint_bits':endpoint_bits,'state_bits':state_bits,
        'oracle':dict(value=str(oracle['value']),leaves=oracle['leaves'],tree_states=oracle['tree_states'],event_evaluations=oracle['event_evaluations']),
        'branch_bound':dict(bb,value=str(bb['value'])),'heuristics':heuristic_results,
        'timing_clock':'perf_counter_ns; elapsed wall time','timing_ns':raw,'counts':counts,'cpu_seconds':time.process_time()-start,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
    return cert,evidence

def summarize(results,out):
    fields=['id','group','rounds','events','value','max_frontier','nodes','transitions','certificate_bytes','oracle_leaves','bnb_states','merge_median_us','checker_median_us','sort_median_us','oracle_us','bnb_median_us']+['gap_'+k for k in KINDS]
    records=[]
    for e in results:
        row={k:e[k] for k in ('id','group','rounds','events','value','certificate_bytes')}
        row.update({k:e['checker'][k] for k in ('max_frontier','nodes','transitions')})
        row.update(oracle_leaves=e['oracle']['leaves'],bnb_states=e['branch_bound']['tree_states'])
        for method,key in [('merge','merge_median_us'),('checker','checker_median_us'),('sort','sort_median_us'),('oracle','oracle_us'),('branch-bound','bnb_median_us')]:row[key]=statistics.median(e['timing_ns'][method])/1000
        for kind in KINDS:row['gap_'+kind]=float(F(e['heuristics'][kind]['relative_gap']))
        records.append(row)
    with (out/'cases.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
    def cost(method):
        med=[statistics.median(r['timing_ns'][method])/1000 for r in results]
        all_t=[x/1000 for r in results for x in r['timing_ns'][method]]
        return {'median_case_us':statistics.median(med),'min_case_us':min(med),'max_case_us':max(med),
                'min_sample_us':min(all_t),'max_sample_us':max(all_t),'total_measured_wall_seconds':sum(all_t)/1e6}
    summary={'instances':len(results),'oracle_agreement':len(results),'whole_frontier_agreement':len(results),
        'oracle_leaves':sum(e['oracle']['leaves'] for e in results),
        'oracle_tree_states':sum(e['oracle']['tree_states'] for e in results),
        'merge_transitions_once':sum(e['checker']['transitions'] for e in results),
        'certificate_nodes':sum(e['checker']['nodes'] for e in results),
        'checker_obligations_once':sum(e['checker']['obligations'] for e in results),
        'max_frontier':max(e['checker']['max_frontier'] for e in results),
        'max_certificate_bytes':max(e['certificate_bytes'] for e in results),
        'max_endpoint_bits':max(e['endpoint_bits'] for e in results),
        'max_state_bits':max(e['state_bits'] for e in results),
        'counts':{k:sum(e['counts'][k] for e in results) for k in ('search_states','checker_obligations')},
        'cpu_seconds':sum(e['cpu_seconds'] for e in results),
        'peak_rss_kib':max(e['peak_rss_kib'] for e in results),'workers':1,
        'timing':{k:cost(k) for k in results[0]['timing_ns']},
        'heuristics':{},'groups':{},'repeats':REPEATS,'oracle_repeats':1,'timing_clock':'perf_counter_ns; elapsed wall time; process CPU recorded only in aggregate'}
    for k in KINDS:
        gaps=[F(e['heuristics'][k]['relative_gap']) for e in results]
        summary['heuristics'][k]={'optimal_cases':sum(g==0 for g in gaps),'mean_gap':str(sum(gaps)/len(gaps)),'max_gap':str(max(gaps))}
    for group in sorted({e['group'] for e in results}):
        r=[e for e in results if e['group']==group]
        summary['groups'][group]={'instances':len(r),'max_frontier':max(e['checker']['max_frontier'] for e in r),
            'transitions':sum(e['checker']['transitions'] for e in r),'oracle_leaves':sum(e['oracle']['leaves'] for e in r),
            'bnb_states':sum(e['branch_bound']['tree_states'] for e in r),
            'greedy_optimal':sum(e['heuristics']['greedy-makespan']['relative_gap']=='0' for e in r)}
    write_json(out/'summary.json',summary);return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'results'/'campaign')
    parser.add_argument('--resume',action='store_true',help='Reuse fully completed case chunks; never changes inputs.')
    args=parser.parse_args();constrain();out=args.output;out.mkdir(parents=True,exist_ok=True)
    results=[]
    resume_log=out/'resume-checks.json'
    extra=read_json(resume_log) if resume_log.exists() else {'checks':[], 'checker_obligations':0, 'cpu_seconds':0.0}
    for obj in all_instances():
        input_path=ROOT/'inputs'/(obj['id']+'.json')
        if input_path.exists():
            if read_json(input_path)!=obj:raise ValueError('frozen input differs from generator')
        else:write_json(input_path,obj)
        result_path=out/'cases'/(obj['id']+'.json');cert_path=out/'certificates'/(obj['id']+'.json')
        if args.resume and result_path.exists() and cert_path.exists():
            cert=read_json(cert_path);begin=time.process_time();checked=check(obj,cert)
            elapsed=time.process_time()-begin;e=read_json(result_path)
            if e['id']!=obj['id'] or e['value']!=checked['value'] or e['checker']!=checked:
                raise ValueError('resume evidence and checked certificate differ')
            extra['checks'].append({'id':obj['id'],'obligations':checked['obligations'],'cpu_seconds':elapsed})
            extra['checker_obligations']+=checked['obligations'];extra['cpu_seconds']+=elapsed
            write_json(resume_log,extra)
        else:
            cert,e=case(obj);write_json(cert_path,cert);write_json(result_path,e)
        results.append(e)
        if sum(e['counts']['search_states'] for e in results)>200000:raise RuntimeError('per-pass search budget')
        if sum(e['counts']['checker_obligations'] for e in results)+extra['checker_obligations']>250000:raise RuntimeError('per-pass check budget')
    summary=summarize(results,out)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('timing','groups','heuristics')},sort_keys=True))
if __name__=='__main__':main()
