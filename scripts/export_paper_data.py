#!/usr/bin/env python3
"""Export data-derived LaTeX tables and a trace diagram without a paper dependency."""
import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def write_table(path: Path, columns: str, header: str, rows: list[str]) -> None:
    path.write_text('\n'.join([r'\begin{tabular}{'+columns+'}', r'\toprule',
        header+r'\\\midrule', *rows, r'\bottomrule', r'\end{tabular}'])+'\n', newline='\n')

def trace_diagram(path: Path) -> None:
    data = json.loads((ROOT/'results/pairing-boundary.json').read_text())
    out = [r'\begin{tikzpicture}[x=.43cm,y=.48cm,font=\scriptsize,>=Stealth]']
    for base, word, label in [(0, [1,2,1,2], '(a) Paired: 1212'),
                              (-5.4, [1,1,2,2], '(b) Unrestricted: 1122')]:
        trace = next(x['trace'] for x in data['orders'] if x['word'] == word)
        for lane, name in [(2, r'$C_1$'), (1, r'$C_2$'), (0, r'$L$')]:
            y = base + lane
            out.append(fr'\draw[gray] (0,{y:g})--(17,{y:g});'
                       fr'\node[anchor=east] at (-.3,{y+.3:g}) {{{name}}};')
        for event in trace:
            stream, k = event['stream'], event['round']
            for kind, y, fill in [('compute', base+3-stream, 'white'),
                                  ('transfer', base, 'black!12')]:
                left, right = event[kind+'_start'], event[kind+'_end']
                symbol = 'C' if kind == 'compute' else 'T'
                text = f'${symbol}_{{{stream}{k}}}$'
                out.append(fr'\draw[fill={fill}] ({left:g},{y+.04:g}) rectangle '
                    fr'({right:g},{y+.6:g});\node at ({(left+right)/2:g},{y+.32:g}) {{{text}}};')
        out.append(fr'\draw[->] (0,{base-.55:g})--(17.8,{base-.55:g});')
        for x in [0,5,10,13,17]:
            out.append(fr'\draw ({x},{base-.55:g})--({x},{base-.7:g}) node[below] {{{x}}};')
        out.append(fr'\node[anchor=west] at (0,{base+3.1:g}) {{{label}}};')
    out.append(r'\end{tikzpicture}')
    path.write_text('\n'.join(out)+'\n', newline='\n')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--campaign', type=Path, default=ROOT/'results/host-campaign')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    summary = json.loads((args.campaign/'summary.json').read_text())
    validation = json.loads((ROOT/'results/validation.json').read_text())
    with (args.output/'widths.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['round','width'])
        writer.writerows(enumerate(validation['sharp_widths'],1))
    labels = {'source-inspired':'Source-inspired','sharp':'Sharp','reset':'Reset',
              'compute-heavy':'Compute-heavy','link-heavy':'Link-heavy',
              'asymmetric':'Asymmetric','mixed-rational':'Mixed rational'}
    rows = []
    for key, label in labels.items():
        group = summary['groups'][key]
        rows.append(f"{label} & {group['instances']} & {group['max_frontier']} & "
                    f"{group['transitions']} & {group['oracle_leaves']:,} & {group['bnb_states']}"+r'\\')
    write_table(args.output/'group-table.tex','lrrrrr',
                r'Family & Cases & Width & Trans. & Words & B\&B',rows)
    rows = []
    for key, label in [('merge','Merge frontier'),('checker','Checker'),('sort','Sorting frontier'),
                       ('branch-bound','Branch-and-bound'),('oracle','Full-DAG oracle')]:
        timing = summary['timing'][key]
        rows.append(label+' & '+' & '.join(f'{timing[k]:,.1f}' for k in
             ['median_case_us','min_case_us','max_case_us'])+r'\\')
    write_table(args.output/'timing-table.tex','lrrr',
                'Method & Median case & Min. case & Max. case',rows)
    rows = []
    for record in sorted((args.campaign/'cases').glob('*.json')):
        case = json.loads(record.read_text())
        check = case['checker']
        rows.append(' & '.join([case['id'],labels[case['group']],str(case['rounds']),
          '$'+case['value']+'$',str(check['max_frontier']),str(check['nodes']),
          str(check['transitions']),f"{case['oracle']['leaves']:,}",str(case['branch_bound']['tree_states'])])+r'\\')
    if len(rows) != 36:
        raise ValueError('Expected exactly 36 retained case records')
    write_table(args.output/'case-table.tex','llrrrrrrr',
                r'Case & Family & Rounds & Exact value & Width & Nodes & Trans. & Words & B\&B',rows)
    unrestricted = json.loads((ROOT/'results/unrestricted-baseline.json').read_text())
    rows = []
    for case in unrestricted['cases']:
        if not case['improved']:
            continue
        pct = 100.0 * float(Fraction(case['relative_gap']))
        rows.append(' & '.join([case['id'], str(case['rounds']), '$'+case['paired_value']+'$',
                    '$'+case['unrestricted_value']+'$', '$'+case['absolute_gap']+'$',
                    f'{pct:.3f}\\%'])+r'\\')
    if len(rows) != unrestricted['improved_cases']:
        raise ValueError('Unrestricted improvement count disagrees with retained summary')
    write_table(args.output/'unrestricted-table.tex','lrrrrr',
                r'Case & Rounds & Paired & All shuffles & Reduction & Relative',rows)
    trace_diagram(args.output/'pairing-boundary.tex')
    print('Exported exact plot/table inputs, unrestricted comparison, and trace-derived pairing diagram.')

if __name__ == '__main__':
    main()
