"""Exact input model. No device timing, external dependencies, or inference."""
from fractions import Fraction
from typing import Any

LIMITS = dict(events=48, edges=96, decisions=12, endpoint_bits=64, certificate_nodes=100000)

def rational(x: Any, *, endpoint: bool = False) -> Fraction:
    if not isinstance(x, str) or len(x) > 2200:
        raise ValueError('rational must be a bounded string')
    try:
        z = Fraction(x)
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError('invalid rational') from e
    if endpoint and max(abs(z.numerator).bit_length(), z.denominator.bit_length()) > 64:
        raise ValueError('endpoint exceeds 64 bits')
    if max(abs(z.numerator).bit_length(), z.denominator.bit_length()) > 3200:
        raise ValueError('rational exceeds path-arithmetic limit')
    return z

def decode(obj: dict, endpoint: str = 'hi') -> list[tuple[Fraction, ...]]:
    allowed={'id','grammar','resources','stages','group','source_schema','duration_provenance'}
    if not isinstance(obj,dict) or set(obj)-allowed:
        raise ValueError('unsupported input fields')
    if not isinstance(obj.get('id'),str) or not 1<=len(obj['id'])<=128:
        raise ValueError('invalid instance identity')
    if endpoint not in ('lo','hi'):
        raise ValueError('invalid endpoint selection')
    if obj.get('grammar') != 'paired-two-chain' or obj.get('resources') != ['C1','C2','L']:
        raise ValueError('unsupported grammar or resources')
    rows = obj.get('stages')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 12:
        raise ValueError('invalid stage count')
    answer=[]
    for row in rows:
        if not isinstance(row,dict) or set(row) != {'c1','c2','p1','p2'}:
            raise ValueError('invalid stage')
        z=[]
        for key in ('c1','c2','p1','p2'):
            v=row[key]
            if not isinstance(v,dict) or set(v) != {'lo','hi'}:
                raise ValueError('invalid interval')
            lo,hi=(rational(v[e],endpoint=True) for e in ('lo','hi'))
            if not 0 <= lo <= hi or hi <= 0:
                raise ValueError('durations must have positive upper endpoint')
            z.append(hi if endpoint=='hi' else lo)
        answer.append(tuple(z))
    # The base two chains have 4m-2 arcs. A full link order adds 2m-1.
    if 4*len(rows)>48 or 6*len(rows)-3>96:
        raise ValueError('event or edge cap exceeded')
    return answer

def step(xy: tuple[Fraction,Fraction], row: tuple[Fraction,...], bit: int):
    x,y=xy; a,b,p,q=row
    if bit==0:
        u=max(x+a,y)+p
        return (u,max(y+b,u)+q)
    if bit==1:
        v=max(y+b,x)+q
        return (max(x+a,v)+p,v)
    raise ValueError('order must be binary')
