"""Exhaustive oracle using full event-DAG relaxation, separate from propagation."""
from fractions import Fraction as F
from itertools import product

def event_graph(rows,orders):
    m=len(rows);dur=[];edges=[]
    for k,row in enumerate(rows):
        dur.extend(row);base=4*k
        edges.extend([(base,base+2),(base+1,base+3)])
        if k:edges.extend([(base-2,base),(base-1,base+1)])
    link=[]
    for k,b in enumerate(orders):link.extend((4*k+2,4*k+3) if b==0 else (4*k+3,4*k+2))
    edges.extend(zip(link,link[1:]))
    return dur,list(edges)

def replay(rows,orders):
    dur,edges=event_graph(rows,orders);n=len(dur)
    pred=[[] for _ in dur]
    for a,b in edges:pred[b].append(a)
    # Repeated topological passes intentionally avoid the solver's stage recurrence.
    finish={};todo=set(range(n))
    while todo:
        progress=False
        for i in sorted(todo):
            if all(p in finish for p in pred[i]):
                finish[i]=max((finish[p] for p in pred[i]),default=F(0))+dur[i]
                todo.remove(i);progress=True
        if not progress:raise ValueError('cycle in event graph')
    return (finish[n-2],finish[n-1])

def exhaustive(rows):
    best=None;front=[];leaves=0;points=set()
    for orders in product((0,1),repeat=len(rows)):
        pair=replay(rows,orders);leaves+=1;points.add(pair)
        if best is None or max(pair)<best:best=max(pair)
    for x,y in sorted(points):
        if not front or y<front[-1][1]:front.append((x,y))
    return {'value':best,'frontier':front,'leaves':leaves,'tree_states':2*leaves-1,
            'event_evaluations':4*len(rows)*leaves}
