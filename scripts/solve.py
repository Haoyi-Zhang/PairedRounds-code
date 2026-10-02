#!/usr/bin/env python3
"""Generate a local exact certificate; use check_certificate.py to validate it."""
import argparse,sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from budget import constrain
from io_contract import read_json,write_json
from solver import solve

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();constrain()
    try:write_json(args.output,solve(read_json(args.input,1024*1024)))
    except (ValueError,OSError,UnicodeError,RecursionError) as exc:
        print(str(exc),file=sys.stderr);return 2
    print(args.output);return 0
if __name__=='__main__':sys.exit(main())
