#!/usr/bin/env python3
"""Bounded reset-condition regression, separate from the frozen timing campaign."""
import itertools
import json
import resource
import sys
import time
from fractions import Fraction as F
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from budget import constrain
from checker import check
from generation import make
from io_contract import write_json
from oracle import exhaustive, replay
from solver import solve


def run():
    begin = time.process_time()
    counts = {"instances": 0, "oracle_words": 0, "merge_transitions": 0,
              "checker_obligations": 0, "both_reset_instances": 0,
              "only_12_reset_instances": 0, "only_21_reset_instances": 0,
              "only_12_width_three": 0, "only_21_width_three": 0}

    def compare(rows, identity):
        obj = make(identity, rows, "reset-regression")
        cert = solve(obj)
        checked = check(obj, cert)
        oracle = exhaustive(rows)
        front = [tuple(map(F, node["xy"])) for node in cert["layers"][-1]["states"]]
        if front != oracle["frontier"] or F(checked["value"]) != oracle["value"]:
            raise AssertionError("reset whole-frontier mismatch")
        counts["instances"] += 1
        counts["oracle_words"] += oracle["leaves"]
        counts["merge_transitions"] += cert["transitions"]
        counts["checker_obligations"] += checked["obligations"]
        return front, [len(layer["states"]) for layer in cert["layers"]]

    witnesses = []
    deadline_queries = 0
    for rows, expected, condition in [
        ([(1, 1, 1, 2), (3, 1, 1, 1)], [(6, 7), (7, 6), (8, 5)], "b<=p"),
        ([(1, 1, 2, 1), (1, 3, 1, 1)], [(5, 8), (6, 7), (7, 6)], "a<=q"),
    ]:
        front, widths = compare(rows, "one-sided-reset")
        if front != expected or widths != [1, 2, 3]:
            raise AssertionError("one-sided reset counterexample changed")
        all_points = [replay(rows, word) for word in itertools.product((0, 1), repeat=2)]
        for d1, d2 in itertools.product(range(10), repeat=2):
            represented = any(x <= d1 and y <= d2 for x, y in front)
            reachable = any(x <= d1 and y <= d2 for x, y in all_points)
            if represented != reachable:
                raise AssertionError("terminal deadline query mismatch")
            deadline_queries += 1
        witnesses.append({"rows": rows, "condition": condition,
                          "frontier": [[str(x), str(y)] for x, y in front], "widths": widths})

    duration_rows = list(itertools.product(range(1, 4), repeat=4))
    for rows in itertools.product(duration_rows, repeat=2):
        front, widths = compare(rows, "finite-reset")
        reset12 = all(b <= p for a, b, p, q in rows)
        reset21 = all(a <= q for a, b, p, q in rows)
        if reset12 and reset21:
            counts["both_reset_instances"] += 1
            if max(widths) > 2:
                raise AssertionError("both-reset width-two guarantee failed")
        elif reset12:
            counts["only_12_reset_instances"] += 1
            counts["only_12_width_three"] += len(front) == 3
        elif reset21:
            counts["only_21_reset_instances"] += 1
            counts["only_21_width_three"] += len(front) == 3
    if counts["instances"] != 6563 or counts["both_reset_instances"] != 1296:
        raise AssertionError("finite reset domain coverage changed")
    if not counts["only_12_width_three"] or not counts["only_21_width_three"]:
        raise AssertionError("one-sided controls were not exercised")
    return {"scope": "separate finite reset regression; not an arbitrary-depth proof or timing campaign",
            "counts": counts, "witnesses": witnesses, "deadline_queries": deadline_queries,
            "cpu_seconds": time.process_time() - begin,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "workers": 1}


if __name__ == "__main__":
    constrain()
    result = run()
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/reproduction-reset-conditions.json"
    write_json(output, result)
    print(json.dumps(result, sort_keys=True))
