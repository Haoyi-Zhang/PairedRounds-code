#!/usr/bin/env python3
"""Check newly authored, source-inspired macro contracts; not CUDA verification."""
import argparse,copy,itertools,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from budget import constrain
from generation import all_instances
from io_contract import read_json,write_json

def build(obj):
    m=len(obj['stages']);events=[];edges=[]
    for i in (1,2):
        chain=[]
        for k in range(1,m+1):
            for kind in ('C','T'):
                name=f'{kind}{i}.{k}';chain.append(name)
                events.append({'id':name,'resource':f'C{i}' if kind=='C' else 'L',
                               'round':k,'stream':i,'kind':kind})
        edges.extend([list(pair) for pair in zip(chain,chain[1:])])
    return {'id':obj['id'],'source_schema':obj['source_schema'],'rounds':m,
        'source':'arXiv:2511.13940, Appendix D and transfer/scheduling discussion',
        'origin':'newly authored restricted abstraction; not a CUDA extraction',
        'completion':'required-data-and-notification-complete','target':'private-point-to-point',
        'link_policy':'paired-rounds','duration_dependence':'independent-of-overlap',
        'initial_data':'ready','events':events,'chain_edges':edges}

def validate(s,obj):
    expected=build(obj)
    if s!=expected:raise ValueError('unsupported macro contract')
    nodes=[n['id'] for n in s['events']];m=s['rounds'];words=0;max_edges=0
    for bits in itertools.product((0,1),repeat=m):
        order=[]
        for k,b in enumerate(bits,1):order.extend([f'T{1+b}.{k}',f'T{2-b}.{k}'])
        edges={tuple(e) for e in s['chain_edges']}|set(zip(order,order[1:]))
        incoming={n:set() for n in nodes}
        for a,b in edges:incoming[b].add(a)
        done=set()
        while len(done)<len(nodes):
            ready={n for n in nodes if n not in done and incoming[n]<=done}
            if not ready:raise ValueError('cyclic event contract')
            done.update(ready)
        assert len(nodes)==4*m and len(edges)<=6*m-3
        words+=1;max_edges=max(max_edges,len(edges))
    return words,max_edges

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results/source-schemas.json'))
    args=parser.parse_args()
    constrain();start=time.process_time();instances=[x for x in all_instances() if x['group']=='source-inspired']
    rows=[];rejected=[]
    for obj in instances:
        s=build(obj);p=ROOT/'source_schemas'/(obj['id']+'.json')
        if p.exists() and read_json(p)!=s:raise ValueError('frozen schema changed')
        write_json(p,s);words,edges=validate(s,obj)
        rows.append({'id':obj['id'],'rounds':s['rounds'],'events':len(s['events']),'edge_bound':edges,'order_words':words})
    o=instances[0];s=build(o)
    muts={
      'missing-chain-edge':lambda x:x['chain_edges'].pop(),
      'extra-cross-compute-wait':lambda x:x['chain_edges'].append(['T2.1','C1.2']),
      'third-compute-resource':lambda x:x['events'][0].update(resource='C3'),
      'launch-only-completion':lambda x:x.update(completion='launch-return'),
      'collective-target':lambda x:x.update(target='all-reduce'),
      'unpaired-link-policy':lambda x:x.update(link_policy='arbitrary-shuffle'),
      'contingent-duration':lambda x:x.update(duration_dependence='depends-on-overlap')}
    for name,f in muts.items():
        bad=copy.deepcopy(s);f(bad)
        try:validate(bad,o)
        except ValueError:rejected.append(name)
        else:raise AssertionError('mutation accepted: '+name)
    report={'scope':'restricted declared macro contracts, not CUDA extraction or hardware validation',
      'schemas':rows,'schema_count':len(rows),'order_words':sum(r['order_words'] for r in rows),
      'mutations_rejected':rejected,'search_states':sum(2*r['order_words']-1 for r in rows),
      'checker_obligations':sum(r['order_words']*(r['events']+r['edge_bound']) for r in rows)+len(muts),
      'cpu_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
    output=args.output if args.output.is_absolute() else ROOT/args.output
    write_json(output,report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
