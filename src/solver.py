"""Linear-merge Pareto propagation and a reachability/coverage certificate."""
from fractions import Fraction as F
from heapq import merge
from model import decode, step

def image_sorted(front, row, bit):
    a,b,p,q=row
    A,B=(a+p,p) if bit==0 else (max(a,q)+p,b+q+p)
    split=0
    while split<len(front) and front[split][0]+A<front[split][1]+B:
        split+=1
    def item(i):
        x,y=step(front[i],row,bit)
        return (x,y,i,bit)
    left=(item(i) for i in range(split-1,-1,-1))
    right=(item(i) for i in range(split,len(front)))
    return merge(left,right)

def solve(obj):
    rows=decode(obj); front=[(F(0),F(0))]
    layers=[{'states':[{'xy':['0','0'],'parent':None,'order':None}]}]
    transitions=0
    for k,row in enumerate(rows,1):
        nxt=[]; entries=[]; cover=[[None,None] for _ in front]
        for x,y,parent,bit in merge(image_sorted(front,row,0),image_sorted(front,row,1)):
            transitions+=1
            if not nxt or y<nxt[-1][1]:
                nxt.append((x,y))
                entries.append({'xy':[str(x),str(y)],'parent':parent,'order':bit})
            cover[parent][bit]=len(nxt)-1
        if len(nxt)>k+1:
            raise AssertionError('linear frontier theorem falsified')
        layers.append({'states':entries,'cover':cover})
        front=nxt
    best=min(range(len(front)),key=lambda i:(max(front[i]),front[i]))
    cur=best; orders=[]
    for layer in reversed(layers[1:]):
        node=layer['states'][cur];orders.append(node['order']);cur=node['parent']
    orders.reverse()
    return {'instance_id':obj['id'],'layers':layers,'terminal':best,
            'lower_bound':str(max(front[best])),'upper_bound':str(max(front[best])),
            'orders':orders,'transitions':transitions}

def sort_reference(obj):
    front=[(F(0),F(0))];states=0
    for row in decode(obj):
        candidates=sorted(set(step(x,row,b) for x in front for b in (0,1)))
        states+=2*len(front);front=[]
        for x,y in candidates:
            if not front or y<front[-1][1]:front.append((x,y))
    return front,states
