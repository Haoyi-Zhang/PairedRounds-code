"""Independent certificate checker: no imports from solver, model, or baselines.

Checks a four-event precedence graph for every transition; verifies coverage and
reachability separately. This is an independently implemented checker, not an
independent scientific review or a formally verified Python implementation.
"""
from fractions import Fraction

# (topological order, predecessors) for the two admitted local event DAGs.
# Both computations precede their own transfer; the transfers share one link.
LOCAL_GRAPHS=(
    ((0,1,2,3),((),(),(0,),(1,2))),
    ((0,1,3,2),((),(),(0,3),(1,))),
)

class InvalidCertificate(ValueError):
    pass

def require(test,message):
    if not test: raise InvalidCertificate(message)

def number(s,limit=3200):
    require(isinstance(s,str) and len(s)<=2200,'bad rational string')
    try:z=Fraction(s)
    except (ValueError,ZeroDivisionError) as exc:raise InvalidCertificate('bad rational') from exc
    require(abs(z.numerator).bit_length()<=limit and z.denominator.bit_length()<=limit,'number too large')
    return z

def input_rows(obj):
    require(isinstance(obj,dict),'input is not an object')
    require(not (set(obj)-{'id','grammar','resources','stages','group','source_schema','duration_provenance'}),'unsupported input fields')
    require(isinstance(obj.get('id'),str) and 1<=len(obj['id'])<=128,'bad identity')
    require(obj.get('grammar')=='paired-two-chain','unsupported grammar')
    require(obj.get('resources')==['C1','C2','L'],'unsupported resources')
    stages=obj.get('stages');require(isinstance(stages,list) and 1<=len(stages)<=12,'stage cap')
    rows=[]
    for s in stages:
        require(isinstance(s,dict) and set(s)=={'c1','c2','p1','p2'},'stage keys')
        row=[]
        for key in ('c1','c2','p1','p2'):
            v=s[key];require(isinstance(v,dict) and set(v)=={'lo','hi'},'interval keys')
            lo,hi=number(v['lo'],64),number(v['hi'],64)
            require(0<=lo<=hi and hi>0,'invalid duration')
            row.append(hi)
        rows.append(row)
    return rows

def transition(entry,durations,order):
    require(type(order) is int and order in (0,1),'nonbinary order')
    # Nodes: compute 1, compute 2, transfer 1, transfer 2.
    topo,predecessors=LOCAL_GRAPHS[order]
    link_release=max(entry)
    starts=[entry[0],entry[1],link_release,link_release];finish=[None]*4
    for u in topo:
        for parent in predecessors[u]:
            starts[u]=max(starts[u],finish[parent])
        finish[u]=starts[u]+durations[u]
    require(finish[2]<=starts[3] if order==0 else finish[3]<=starts[2],'link overlap')
    return (finish[2],finish[3])

def check(obj,cert):
    rows=input_rows(obj);require(isinstance(cert,dict),'certificate must be an object')
    require(set(cert)=={'instance_id','layers','terminal','lower_bound','upper_bound','orders','transitions'},'certificate keys')
    require(cert.get('instance_id')==obj.get('id'),'instance identity mismatch')
    layers=cert.get('layers');require(isinstance(layers,list) and len(layers)==len(rows)+1,'missing layer')
    require(all(isinstance(l,dict) and isinstance(l.get('states'),list) for l in layers),'invalid layer object')
    require(sum(len(l['states']) for l in layers)<=100000,'certificate node cap')
    require(layers[0]=={'states':[{'xy':['0','0'],'parent':None,'order':None}]},'initial state')
    previous=[(Fraction(0),Fraction(0))];obligations=1;transitions=0
    parsed=[previous]
    for k,d in enumerate(rows,1):
        layer=layers[k];require(set(layer)=={'states','cover'},'layer keys');nodes=layer.get('states')
        require(isinstance(nodes,list) and 1<=len(nodes)<=k+1,'frontier width')
        current=[]
        evaluated={}
        def replay_parent(parent,order):
            # Validate BEFORE lookup: bool and int compare equal in Python.
            require(type(order) is int and order in (0,1),'nonbinary order')
            key=(parent,order)
            if key not in evaluated:
                evaluated[key]=transition(previous[parent],d,order)
            return evaluated[key]
        for node in nodes:
            require(isinstance(node,dict) and set(node)=={'xy','parent','order'},'node keys')
            xy=node['xy'];require(isinstance(xy,list) and len(xy)==2,'state coordinate count')
            pair=tuple(number(s) for s in xy)
            parent=node['parent'];require(type(parent) is int and 0<=parent<len(previous),'bad parent')
            expected=replay_parent(parent,node['order']);obligations+=9
            require(pair==expected,'unreachable retained state')
            if current:require(current[-1][0]<pair[0] and current[-1][1]>pair[1],'not a strict antichain')
            current.append(pair)
        cover=layer.get('cover')
        require(isinstance(cover,list) and len(cover)==len(previous),'missing predecessor coverage')
        for i,entry in enumerate(previous):
            require(isinstance(cover[i],list) and len(cover[i])==2,'missing binary branch')
            for order in (0,1):
                index=cover[i][order];require(type(index) is int and 0<=index<len(current),'invalid dominator')
                candidate=replay_parent(i,order);transitions+=1;obligations+=11
                require(all(a<=b for a,b in zip(current[index],candidate)),'false domination')
        previous=current;parsed.append(current)
    terminal=cert.get('terminal');require(type(terminal) is int and 0<=terminal<len(previous),'terminal')
    value=min(max(s) for s in previous)
    require(max(previous[terminal])==value,'nonminimal terminal')
    require(number(cert.get('lower_bound'))==value==number(cert.get('upper_bound')),'false bounds')
    require(type(cert.get('transitions')) is int and cert['transitions']==transitions,'transition count')
    orders=cert.get('orders');require(isinstance(orders,list) and len(orders)==len(rows),'order sequence')
    state=(Fraction(0),Fraction(0))
    for d,b in zip(rows,orders):state=transition(state,d,b);obligations+=9
    require(max(state)==value,'incumbent does not attain bound')
    return {'verified':True,'value':str(value),'obligations':obligations,
            'nodes':sum(map(len,parsed)),'transitions':transitions,'max_frontier':max(map(len,parsed))}
