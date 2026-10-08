"""Dynamic adjacency/queue evaluator for the same four-node event contract."""
from collections import deque
import importlib.util
from pathlib import Path

def transition(entry,durations,order):
    if type(order) is not int or order not in (0,1):
        raise ValueError('nonbinary order')
    edges=[(0,2),(1,3),(2,3) if order==0 else (3,2)]
    release=[entry[0],entry[1],max(entry),max(entry)]
    successors=[[] for _ in range(4)];indegree=[0]*4;starts=release[:]
    for u,v in edges:
        successors[u].append(v);indegree[v]+=1
    ready=deque(i for i in range(4) if indegree[i]==0)
    finish=[None]*4;seen=0
    while ready:
        u=ready.popleft();finish[u]=starts[u]+durations[u];seen+=1
        for v in successors[u]:
            starts[v]=max(starts[v],finish[u]);indegree[v]-=1
            if indegree[v]==0:ready.append(v)
    if seen!=4:
        raise ValueError('cyclic local graph')
    if not (finish[2]<=starts[3] if order==0 else finish[3]<=starts[2]):
        raise ValueError('link overlap')
    return finish[2],finish[3]

def checker_module():
    """Use identical admission/coverage logic, changing only the DAG evaluator."""
    path=Path(__file__).resolve().parents[1]/'src/checker.py'
    spec=importlib.util.spec_from_file_location('dynamic_graph_checker',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.transition=transition
    return module
