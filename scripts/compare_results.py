#!/usr/bin/env python3
"""Compare exact scientific outputs; never require noisy wall times to agree."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('reproduction',type=Path);a=p.parse_args()
    exact=('id','group','source_schema','rounds','events','edge_bound','value','terminal_frontier','widths','checker','certificate_bytes','endpoint_bits','state_bits','oracle','branch_bound','heuristics','counts')
    names=sorted(x.name for x in (a.reference/'cases').glob('*.json'))
    if len(names)!=36 or names!=sorted(x.name for x in (a.reproduction/'cases').glob('*.json')):raise ValueError('case set differs')
    for name in names:
        x=json.loads((a.reference/'cases'/name).read_text());y=json.loads((a.reproduction/'cases'/name).read_text())
        if any(x[k]!=y[k] for k in exact):raise ValueError('exact evidence differs: '+name)
        if json.loads((a.reference/'certificates'/name).read_text())!=json.loads((a.reproduction/'certificates'/name).read_text()):raise ValueError('certificate differs: '+name)
    print(json.dumps({'exact_cases_equal':len(names),'certificates_equal':len(names),'wall_clock_equality_required':False},sort_keys=True))
if __name__=='__main__':main()
