#!/usr/bin/env python3
"""Check an input/certificate pair independently of the optimizer."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from budget import constrain
from io_contract import read_json
from checker import check

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('certificate',type=Path)
    args=parser.parse_args();constrain()
    try:
        result=check(read_json(args.input,1024*1024),read_json(args.certificate))
    except (ValueError,OSError,UnicodeError,RecursionError) as exc:
        print(json.dumps({'verified':False,'error':str(exc)}));return 2
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':sys.exit(main())
