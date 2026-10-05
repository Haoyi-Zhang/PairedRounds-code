#!/usr/bin/env python3
"""Finite validation for the exact all-shuffles progress-grid baseline."""
import copy
import itertools
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
from model import decode
from solver import solve
from unrestricted_grid import solve_unrestricted
from unrestricted_checker import InvalidGridCertificate, check_unrestricted
from io_contract import write_json


def replay(rows, word):
    used = [0, 0]
    x = y = F(0)
    for stream in word:
        index = stream - 1
        row = rows[used[index]]
        a, b, p, q = row
        if stream == 1:
            x = max(x + a, y) + p
        else:
            y = max(y + b, x) + q
        used[index] += 1
    return (x, y)


def full_shuffle_frontier(rows):
    m = len(rows)
    candidates = set()
    words = 0
    for positions in itertools.combinations(range(2 * m), m):
        selected = set(positions)
        word = [1 if i in selected else 2 for i in range(2 * m)]
        candidates.add(replay(rows, word))
        words += 1
    front = []
    for x, y in sorted(candidates):
        if not front or y < front[-1][1]:
            front.append((x, y))
    return front, words


def run():
    begin = time.process_time()
    cases = []
    counts = {"search_states": 0, "checker_obligations": 0}
    full_words = 0
    for obj in all_instances():
        rows = decode(obj)
        paired = solve(obj)
        counts["search_states"] += paired["transitions"]
        cert = solve_unrestricted(obj)
        checked = check_unrestricted(obj, cert)
        terminal = [tuple(F(z) for z in xy) for xy in checked["terminal_frontier"]]
        exact_words = None
        if len(rows) <= 7:
            oracle, exact_words = full_shuffle_frontier(rows)
            if terminal != oracle:
                raise AssertionError("unrestricted whole-frontier mismatch: " + obj["id"])
            if F(checked["value"]) != min(max(xy) for xy in oracle):
                raise AssertionError("unrestricted optimum mismatch: " + obj["id"])
            full_words += exact_words
            counts["search_states"] += exact_words
        p = F(paired["upper_bound"])
        u = F(checked["value"])
        if u > p:
            raise AssertionError("broader grammar cannot be worse")
        counts["search_states"] += cert["generated_transitions"]
        counts["checker_obligations"] += checked["obligations"]
        cases.append(
            {
                "id": obj["id"],
                "group": obj["group"],
                "rounds": len(rows),
                "paired_value": str(p),
                "unrestricted_value": str(u),
                "absolute_gap": str(p - u),
                "relative_gap": str((p - u) / p),
                "improved": u < p,
                "word": cert["word"],
                "terminal_frontier": checked["terminal_frontier"],
                "cells": checked["cells"],
                "nodes": checked["nodes"],
                "max_frontier": checked["max_frontier"],
                "generated_transitions": checked["generated_transitions"],
                "coverage_pointers": checked["coverage_pointers"],
                "checker_obligations": checked["obligations"],
                "full_shuffle_words": exact_words,
            }
        )

    # Mutation attacks target every obligation class added by this certificate.
    obj = all_instances()[0]
    valid = solve_unrestricted(obj)
    counts["search_states"] += valid["generated_transitions"]
    mutations = []
    def add(name, change):
        cert = copy.deepcopy(valid)
        change(cert)
        mutations.append((name, cert))
    add("wrong-identity", lambda c: c.__setitem__("instance_id", "other"))
    add("unreachable-node", lambda c: c["cells"][1][0]["states"][0]["xy"].__setitem__(0, "0"))
    add("bad-parent", lambda c: c["cells"][1][0]["states"][0].__setitem__("parent", 99))
    add("bad-stream", lambda c: c["cells"][1][0]["states"][0].__setitem__("stream", 2))
    add("missing-coverage", lambda c: c["cells"][0][0]["cover1"].clear())
    add("false-dominator", lambda c: c["cells"][0][0]["cover1"].__setitem__(0, 99))
    add("false-bound", lambda c: c.__setitem__("lower_bound", "0"))
    add("bad-word", lambda c: c["word"].__setitem__(0, 2 if c["word"][0] == 1 else 1))
    mutation_results = []
    valid_checked = check_unrestricted(obj, valid)
    counts["checker_obligations"] += valid_checked["obligations"]
    for name, cert in mutations:
        try:
            check_unrestricted(obj, cert)
        except InvalidGridCertificate:
            mutation_results.append({"name": name, "rejected": True})
        else:
            raise AssertionError("accepted unrestricted mutation: " + name)
        counts["checker_obligations"] += valid_checked["obligations"]

    improved = [case for case in cases if case["improved"]]
    max_case = max(cases, key=lambda c: F(c["relative_gap"]))
    return {
        "scope": "post-freeze exact boundary baseline; not merged into the original 36-case timing protocol",
        "instances": len(cases),
        "full_shuffle_oracle_instances": sum(c["full_shuffle_words"] is not None for c in cases),
        "full_shuffle_words": full_words,
        "improved_cases": len(improved),
        "improved_ids": [c["id"] for c in improved],
        "max_relative_gap": max_case["relative_gap"],
        "max_gap_case": max_case["id"],
        "max_absolute_gap": max_case["absolute_gap"],
        "max_frontier": max(c["max_frontier"] for c in cases),
        "total_nodes": sum(c["nodes"] for c in cases),
        "total_generated_transitions": sum(c["generated_transitions"] for c in cases),
        "total_coverage_pointers": sum(c["coverage_pointers"] for c in cases),
        "mutation_results": mutation_results,
        "cases": cases,
        "counts": counts,
        "accounting_version": 2,
        "cpu_seconds": time.process_time() - begin,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
    }


if __name__ == "__main__":
    constrain()
    result = run()
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "unrestricted-grid-validation.json"
    write_json(output, result)
    print(json.dumps({k: result[k] for k in result if k not in ("cases", "mutation_results")}, sort_keys=True))
