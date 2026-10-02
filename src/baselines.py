"""Transparent grammar-restricted baselines, not upstream HEFT implementations."""
from fractions import Fraction as F

def advance(s,r,b):
    release=[s[0]+r[0],s[1]+r[1]];link=max(s);out=[None,None]
    for i in ([0,1] if b==0 else [1,0]):
        link=max(link,release[i])+r[2+i];out[i]=link
    return tuple(out)

def heuristic(rows,kind):
    s=(F(0),F(0));orders=[];count=0
    for k,r in enumerate(rows):
        if kind=='fixed12':b=0
        elif kind=='fixed21':b=1
        elif kind=='earliest-release':b=int(s[1]+r[1]<s[0]+r[0])
        elif kind=='bottom-level':
            # Rank of the transfer includes its duration and its remaining chain.
            ranks=[r[2+i]+sum((t[i]+t[2+i] for t in rows[k+1:]),F(0)) for i in (0,1)]
            b=int(ranks[1]>ranks[0])
        elif kind=='greedy-makespan':
            pairs=[advance(s,r,b) for b in (0,1)];count+=2
            b=min((0,1),key=lambda i:(max(pairs[i]),i))
        else:raise ValueError('unknown baseline')
        s=advance(s,r,b);count+=1;orders.append(b)
    return max(s),orders,count

def branch_bound(rows,cap=1000000):
    best,orders,initial=heuristic(rows,'bottom-level');n=len(rows)
    remaining1=[F(0)]*(n+1);remaining2=remaining1[:];remainingL=remaining1[:]
    for k in range(n-1,-1,-1):
        a,b,p,q=rows[k];remaining1[k]=remaining1[k+1]+a+p;remaining2[k]=remaining2[k+1]+b+q;remainingL[k]=remainingL[k+1]+p+q
    count=0;pruned=0
    def visit(k,s,path):
        nonlocal best,orders,count,pruned
        count+=1
        if count>cap:raise RuntimeError('search cap')
        lb=max(s[0]+remaining1[k],s[1]+remaining2[k],max(s)+remainingL[k])
        if lb>=best:pruned+=1;return
        if k==n:best=max(s);orders=path;return
        children=[(advance(s,rows[k],b),b) for b in (0,1)]
        for state,b in sorted(children,key=lambda t:(max(t[0]),t[1])):visit(k+1,state,path+[b])
    visit(0,(F(0),F(0)),[])
    return {'value':best,'orders':orders,'tree_states':count,'pruned':pruned,'initialization_states':initial}
