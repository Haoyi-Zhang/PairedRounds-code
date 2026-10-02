"""Frozen deterministic schema construction; all durations are synthetic."""
from fractions import Fraction as F
import random

def make(name,rows,group,source='none',width=F(1,4)):
    return {'id':name,'grammar':'paired-two-chain','resources':['C1','C2','L'],
            'group':group,'source_schema':source,'duration_provenance':'synthetic rational values; no device measurements',
            'stages':[{key:{'lo':str(F(v)*(1-width)),'hi':str(F(v))} for key,v in zip(('c1','c2','p1','p2'),r)} for r in rows]}

def sharp_rows(m):
    rows=[(F(1),F(1),F(1),F(1))]
    for k in range(2,m+1):
        delta=F(1,2**(k-1));rows.append((F(2*k-3)+2*delta,F(2*k-1)+delta,F(1),F(1)))
    return rows

def all_instances():
    cases=[]
    # Three explicitly restricted public motifs, at four declared unroll depths.
    motifs=['producer-store','load-consumer-reuse','dedicated-communicator']
    for j,motif in enumerate(motifs):
        for m in (2,4,6,8):
            rows=[]
            for k in range(m):
                if j==0:r=(3+(k%3),2+((2*k)%5),2+(k%2),3)
                elif j==1:r=(2+((3*k)%7),4+(k%3),1+(k%3),2+(k%2))
                else:r=(7+(k%5),5+((2*k)%7),2+(k%2),1+(k%3))
                rows.append(r)
            cases.append(make(f'schema-{len(cases)+1:02}',rows,'source-inspired',motif))
    rng=random.Random(20260915)
    families=['sharp','reset','compute-heavy','link-heavy','asymmetric','mixed-rational']
    for family in families:
        for m in (3,5,7,12):
            if family=='sharp':rows=sharp_rows(m)
            else:
                rows=[]
                for k in range(m):
                    if family=='reset':r=(rng.randint(1,4),rng.randint(1,4),rng.randint(4,10),rng.randint(4,10))
                    elif family=='compute-heavy':r=(rng.randint(10,60),rng.randint(10,60),rng.randint(1,4),rng.randint(1,4))
                    elif family=='link-heavy':r=(rng.randint(1,10),rng.randint(1,10),rng.randint(8,35),rng.randint(8,35))
                    elif family=='asymmetric':r=(rng.randint(1,3),rng.randint(10,50),rng.randint(10,30),rng.randint(1,3)) if k%2==0 else (rng.randint(10,50),rng.randint(1,3),rng.randint(1,3),rng.randint(10,30))
                    else:r=tuple(F(rng.randint(1,100),rng.choice((2,3,5,7,11))) for _ in range(4))
                    rows.append(r)
            cases.append(make(f'stress-{len(cases)-11:02}',rows,family))
    assert len(cases)==36
    return cases
