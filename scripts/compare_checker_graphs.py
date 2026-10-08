#!/usr/bin/env python3
"""Compare dynamic graph construction/traversal with fixed-topology DAG evaluation."""
import argparse
from pathlib import Path
import statistics
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from budget import constrain,environment,peak_rss_kib
from io_contract import read_json,write_json
from dag_reference import checker_module
import checker

BLOCKS=11
CALLS=20
WARMUPS=2

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists():
        raise ValueError('Measurement output must be new; retained samples are not overwritten')
    constrain();cpu_start=time.process_time()
    paths=sorted((ROOT/'inputs').glob('*.json'))
    if len(paths)!=36:
        raise ValueError('Frozen case collection changed')
    cases=[(read_json(path),read_json(ROOT/'results/host-campaign/certificates'/path.name)) for path in paths]
    reference=checker_module()
    methods={'dynamic':reference.check,'compiled':checker.check}
    plan={'blocks':BLOCKS,'calls_per_sample':CALLS,'warmups_per_arm':WARMUPS,
          'cases':[obj['id'] for obj,cert in cases],
          'arm_order':'alternating by case index plus block index',
          'scope':'whole checker with identical admission, layer reuse, obligations and incumbent replay; only local graph evaluator differs',
          'environment':environment(),
          'implementation_text':{'common_checker':(ROOT/'src/checker.py').read_text(encoding='utf-8'),
                                 'dynamic_evaluator':(ROOT/'tests/dag_reference.py').read_text(encoding='utf-8'),
                                 'measurement_driver':Path(__file__).read_text(encoding='utf-8')}}
    # Written before warmup/timing. There is one prescribed campaign, with no
    # omitted slower case, early speedup stop, or adaptive repetition selection.
    write_json(out/'plan.json',plan)
    rows=[]
    for case_index,(obj,cert) in enumerate(cases):
        expected=checker.check(obj,cert)
        if reference.check(obj,cert)!=expected:
            raise AssertionError('Full checker disagreement')
        for method in methods.values():
            for _ in range(WARMUPS):
                if method(obj,cert)!=expected:
                    raise AssertionError('Warmup result disagreement')
        raw={'dynamic':[],'compiled':[]};pairs=[]
        for block in range(BLOCKS):
            order=('dynamic','compiled') if (block+case_index)%2==0 else ('compiled','dynamic')
            pair={}
            for arm in order:
                method=methods[arm];start=time.perf_counter_ns()
                for _ in range(CALLS):
                    result=method(obj,cert)
                elapsed=time.perf_counter_ns()-start
                if result!=expected:
                    raise AssertionError('Measured result disagreement')
                raw[arm].append(elapsed);pair[arm]=elapsed
            pairs.append({'block':block,'first':order[0],**pair})
        dynamic=statistics.median(raw['dynamic'])/CALLS
        compiled=statistics.median(raw['compiled'])/CALLS
        rows.append({'id':obj['id'],'group':obj['group'],'result':expected,
                     'pairs':pairs,'dynamic_median_ns':dynamic,'compiled_median_ns':compiled,
                     'speedup':dynamic/compiled,'relative_reduction':1-compiled/dynamic})
    write_json(out/'cases.json',rows)
    summary={'cases':len(rows),'timed_full_checks_per_arm':len(rows)*BLOCKS*CALLS,
             'compiled_faster_cases':sum(x['compiled_median_ns']<x['dynamic_median_ns'] for x in rows),
             'equal_cases':sum(x['compiled_median_ns']==x['dynamic_median_ns'] for x in rows),
             'compiled_slower_cases':sum(x['compiled_median_ns']>x['dynamic_median_ns'] for x in rows),
             'median_dynamic_us':statistics.median(x['dynamic_median_ns'] for x in rows)/1000,
             'median_compiled_us':statistics.median(x['compiled_median_ns'] for x in rows)/1000,
             'median_paired_relative_reduction':statistics.median(x['relative_reduction'] for x in rows),
             'min_speedup':min(x['speedup'] for x in rows),'max_speedup':max(x['speedup'] for x in rows),
             'cpu_seconds':time.process_time()-cpu_start,'peak_rss_kib':peak_rss_kib(),
             'all_full_checker_results_equal':True}
    write_json(out/'summary.json',summary)
    print(summary)

if __name__=='__main__':
    main()
