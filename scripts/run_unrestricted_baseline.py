#!/usr/bin/env python3
"""Run the post-freeze exact all-shuffles baseline on all frozen inputs."""
import json
import resource
import sys
import time
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from budget import constrain
from generation import all_instances
from solver import solve
from unrestricted_grid import solve_unrestricted
from unrestricted_checker import check_unrestricted
from io_contract import write_json


def main():
    constrain()
    begin = time.process_time()
    cases = []
    search_states = paired_search_states = checker_obligations = 0
    for obj in all_instances():
        paired = solve(obj)
        paired_search_states += paired["transitions"]
        cert = solve_unrestricted(obj)
        checked = check_unrestricted(obj, cert)
        p, u = F(paired["upper_bound"]), F(checked["value"])
        record = {
            "id": obj["id"],
            "group": obj["group"],
            "rounds": len(obj["stages"]),
            "paired_value": str(p),
            "unrestricted_value": str(u),
            "absolute_gap": str(p-u),
            "relative_gap": str((p-u)/p),
            "improved": u < p,
            "word": cert["word"],
            "terminal_frontier": checked["terminal_frontier"],
            "cells": checked["cells"],
            "nodes": checked["nodes"],
            "max_frontier": checked["max_frontier"],
            "generated_transitions": checked["generated_transitions"],
            "coverage_pointers": checked["coverage_pointers"],
            "checker_obligations": checked["obligations"],
            "certificate": cert,
        }
        cases.append(record)
        search_states += checked["generated_transitions"]
        checker_obligations += checked["obligations"]
    improved = [c for c in cases if c["improved"]]
    max_case = max(cases, key=lambda c: F(c["relative_gap"]))
    result = {
        "scope": "post-freeze exact boundary baseline; same 36 inputs, broader all-shuffles grammar",
        "instances": len(cases),
        "improved_cases": len(improved),
        "improved_ids": [c["id"] for c in improved],
        "max_relative_gap": max_case["relative_gap"],
        "max_gap_case": max_case["id"],
        "max_absolute_gap": max_case["absolute_gap"],
        "max_frontier": max(c["max_frontier"] for c in cases),
        "total_nodes": sum(c["nodes"] for c in cases),
        "total_generated_transitions": search_states,
        "search_states": search_states + paired_search_states,
        "paired_search_states": paired_search_states,
        "accounting_version": 2,
        "total_coverage_pointers": sum(c["coverage_pointers"] for c in cases),
        "checker_obligations": checker_obligations,
        "cases": cases,
        "cpu_seconds": time.process_time()-begin,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "unrestricted-baseline.json"
    write_json(output, result)
    print(json.dumps({k:v for k,v in result.items() if k != "cases"}, sort_keys=True))


if __name__ == "__main__":
    main()
