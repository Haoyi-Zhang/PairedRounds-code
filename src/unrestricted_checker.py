"""Independent checker for unrestricted progress-grid certificates.

No imports from model.py or unrestricted_grid.py.  This checks input admission,
reachability, strict antichains, every legal outgoing branch, the witness word, and
matching lower/upper bounds.  It is ordinary Python, not a mechanized verifier.
"""
from fractions import Fraction


class InvalidGridCertificate(ValueError):
    pass


def require(test, message):
    if not test:
        raise InvalidGridCertificate(message)


def number(value, limit=3200):
    require(isinstance(value, str) and len(value) <= 2200, "bad rational string")
    try:
        z = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise InvalidGridCertificate("bad rational") from exc
    require(abs(z.numerator).bit_length() <= limit and z.denominator.bit_length() <= limit, "number too large")
    return z


def input_rows(obj):
    allowed = {"id", "grammar", "resources", "stages", "group", "source_schema", "duration_provenance"}
    require(isinstance(obj, dict) and not (set(obj) - allowed), "unsupported input fields")
    require(isinstance(obj.get("id"), str) and 1 <= len(obj["id"]) <= 128, "bad identity")
    require(obj.get("grammar") == "paired-two-chain", "unsupported input grammar")
    require(obj.get("resources") == ["C1", "C2", "L"], "unsupported resources")
    stages = obj.get("stages")
    require(isinstance(stages, list) and 1 <= len(stages) <= 12, "stage cap")
    rows = []
    for stage in stages:
        require(isinstance(stage, dict) and set(stage) == {"c1", "c2", "p1", "p2"}, "stage keys")
        row = []
        for key in ("c1", "c2", "p1", "p2"):
            interval = stage[key]
            require(isinstance(interval, dict) and set(interval) == {"lo", "hi"}, "interval keys")
            lo, hi = number(interval["lo"], 64), number(interval["hi"], 64)
            require(0 <= lo <= hi and hi > 0, "invalid duration")
            row.append(hi)
        rows.append(tuple(row))
    return rows


def advance(xy, row, stream):
    x, y = xy
    a, b, p, q = row
    require(type(stream) is int and stream in (1, 2), "invalid stream")
    if stream == 1:
        return (max(x + a, y) + p, y)
    return (x, max(y + b, x) + q)


def replay(rows, word):
    require(isinstance(word, list) and len(word) == 2 * len(rows), "bad witness length")
    used = [0, 0]
    xy = (Fraction(0), Fraction(0))
    for stream in word:
        require(type(stream) is int and stream in (1, 2), "bad witness symbol")
        index = stream - 1
        require(used[index] < len(rows), "too many stream events")
        xy = advance(xy, rows[used[index]], stream)
        used[index] += 1
    require(used == [len(rows), len(rows)], "incomplete witness")
    return xy


def check_unrestricted(obj, cert):
    rows = input_rows(obj)
    m = len(rows)
    require(isinstance(cert, dict), "certificate must be an object")
    require(
        set(cert)
        == {
            "instance_id",
            "grammar",
            "cells",
            "terminal",
            "lower_bound",
            "upper_bound",
            "word",
            "generated_transitions",
            "coverage_pointers",
        },
        "certificate keys",
    )
    require(cert["instance_id"] == obj["id"], "identity mismatch")
    require(cert["grammar"] == "all-chain-respecting-link-shuffles", "certificate grammar")
    cells = cert["cells"]
    require(isinstance(cells, list) and len(cells) == m + 1, "cell rows")
    require(all(isinstance(row, list) and len(row) == m + 1 for row in cells), "cell columns")
    initial = cells[0][0]
    require(isinstance(initial, dict) and set(initial) == {"states", "cover1", "cover2"}, "initial cell keys")
    require(
        initial["states"]
        == [{"xy": ["0", "0"], "parent_cell": None, "parent": None, "stream": None}],
        "initial state",
    )

    parsed = [[None for _ in range(m + 1)] for _ in range(m + 1)]
    parsed[0][0] = [(Fraction(0), Fraction(0))]
    obligations = 1
    generated = 0
    coverage = 0
    nodes = 1
    max_frontier = 1

    for total in range(1, 2 * m + 1):
        for i in range(max(0, total - m), min(m, total) + 1):
            j = total - i
            cell = cells[i][j]
            require(isinstance(cell, dict) and set(cell) == {"states", "cover1", "cover2"}, "cell keys")
            raw = cell["states"]
            require(isinstance(raw, list) and raw, "empty frontier")
            current = []
            for node in raw:
                require(
                    isinstance(node, dict) and set(node) == {"xy", "parent_cell", "parent", "stream"},
                    "node keys",
                )
                xy_raw = node["xy"]
                require(isinstance(xy_raw, list) and len(xy_raw) == 2, "coordinate count")
                xy = tuple(number(z) for z in xy_raw)
                stream = node["stream"]
                require(type(stream) is int and stream in (1, 2), "node stream")
                parent_cell = node["parent_cell"]
                require(isinstance(parent_cell, list) and len(parent_cell) == 2, "parent cell")
                pi, pj = parent_cell
                require(type(pi) is int and type(pj) is int, "parent cell type")
                expected_cell = (i - 1, j) if stream == 1 else (i, j - 1)
                require((pi, pj) == expected_cell, "parent cell step")
                parent = node["parent"]
                require(type(parent) is int and 0 <= parent < len(parsed[pi][pj]), "parent index")
                row = rows[i - 1] if stream == 1 else rows[j - 1]
                expected = advance(parsed[pi][pj][parent], row, stream)
                obligations += 7
                require(xy == expected, "unreachable retained state")
                if current:
                    require(current[-1][0] < xy[0] and current[-1][1] > xy[1], "not a strict antichain")
                current.append(xy)
            parsed[i][j] = current
            nodes += len(current)
            require(nodes <= 100000, "certificate node cap")
            max_frontier = max(max_frontier, len(current))

    # Coverage establishes that no reachable label omitted at any cell can improve
    # a terminal monotone objective.
    for i in range(m + 1):
        for j in range(m + 1):
            cell = cells[i][j]
            states = parsed[i][j]
            c1, c2 = cell["cover1"], cell["cover2"]
            require(isinstance(c1, list) and isinstance(c2, list), "coverage arrays")
            require(len(c1) == (len(states) if i < m else 0), "stream-1 coverage length")
            require(len(c2) == (len(states) if j < m else 0), "stream-2 coverage length")
            if i < m:
                target = parsed[i + 1][j]
                for parent, index in enumerate(c1):
                    require(type(index) is int and 0 <= index < len(target), "stream-1 dominator")
                    candidate = advance(states[parent], rows[i], 1)
                    require(target[index][0] <= candidate[0] and target[index][1] <= candidate[1], "false stream-1 domination")
                    obligations += 6
                    generated += 1
                    coverage += 1
            if j < m:
                target = parsed[i][j + 1]
                for parent, index in enumerate(c2):
                    require(type(index) is int and 0 <= index < len(target), "stream-2 dominator")
                    candidate = advance(states[parent], rows[j], 2)
                    require(target[index][0] <= candidate[0] and target[index][1] <= candidate[1], "false stream-2 domination")
                    obligations += 6
                    generated += 1
                    coverage += 1

    require(cert["generated_transitions"] == generated, "transition count")
    require(cert["coverage_pointers"] == coverage, "coverage count")
    terminal_front = parsed[m][m]
    terminal = cert["terminal"]
    require(type(terminal) is int and 0 <= terminal < len(terminal_front), "terminal index")
    value = min(max(xy) for xy in terminal_front)
    lower, upper = number(cert["lower_bound"]), number(cert["upper_bound"])
    require(lower == value == upper, "bound mismatch")
    witness = replay(rows, cert["word"])
    require(max(witness) == upper, "witness mismatch")
    require(witness == terminal_front[terminal], "terminal witness state")
    return {
        "value": str(value),
        "terminal_frontier": [[str(x), str(y)] for x, y in terminal_front],
        "cells": (m + 1) ** 2,
        "nodes": nodes,
        "generated_transitions": generated,
        "coverage_pointers": coverage,
        "obligations": obligations,
        "max_frontier": max_frontier,
    }
