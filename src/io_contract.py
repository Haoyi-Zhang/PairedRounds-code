"""Bounded local JSON I/O; no network operations or implicit executable inputs."""
import json
from pathlib import Path

def _object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result

def read_json(path,limit=8*1024*1024):
    with Path(path).open('rb') as f:data=f.read(limit+1)
    if len(data)>limit:raise ValueError('JSON byte cap exceeded')
    def bad(s):raise ValueError('nonfinite JSON numeric literal')
    return json.loads(data.decode('utf-8'),object_pairs_hook=_object,parse_constant=bad)

def write_json(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n'
    if len(data.encode())>8*1024*1024:raise ValueError('JSON byte cap exceeded')
    p.write_text(data)
