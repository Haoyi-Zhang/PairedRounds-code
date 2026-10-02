"""Exact Pareto dynamic program for all chain-respecting transfer interleavings.

This is a post-freeze boundary baseline.  It solves a broader legal-order class than
paired rounds: the link word may be any shuffle of m stream-1 and m stream-2
transfers that preserves each stream's own order.  It does not import or modify an
upstream geometric scheduler.
"""
from fractions import Fraction as F
from model import decode


def _advance(xy, row, stream):
    """Advance one stream from a progress-grid cell."""
    x, y = xy
    a, b, p, q = row
    if stream == 1:
        return (max(x + a, y) + p, y)
    if stream == 2:
        return (x, max(y + b, x) + q)
    raise ValueError("stream must be 1 or 2")


def _pareto(candidates):
    """Return a deterministic strict antichain and one reachable parent per state."""
    # Candidate tuple: (x, y, parent_i, parent_j, parent_index, stream).
    ordered = sorted(candidates, key=lambda z: (z[0], z[1], z[2], z[3], z[4], z[5]))
    unique = []
    last_xy = None
    for item in ordered:
        if item[:2] != last_xy:
            unique.append(item)
            last_xy = item[:2]
    kept = []
    best_y = None
    for item in unique:
        if best_y is None or item[1] < best_y:
            kept.append(item)
            best_y = item[1]
    return kept


def _dominator(front, candidate):
    """Return a retained index that weakly dominates candidate."""
    for index, state in enumerate(front):
        if state[0] <= candidate[0] and state[1] <= candidate[1]:
            return index
    raise AssertionError("Pareto reduction lost coverage")


def solve_unrestricted(obj):
    """Solve every chain-respecting link shuffle and emit a local coverage certificate."""
    rows = decode(obj)
    m = len(rows)
    cells = [[None for _ in range(m + 1)] for _ in range(m + 1)]
    cells[0][0] = {
        "states": [{"xy": ["0", "0"], "parent_cell": None, "parent": None, "stream": None}],
        "cover1": [],
        "cover2": [],
    }
    generated = 0

    for total in range(1, 2 * m + 1):
        for i in range(max(0, total - m), min(m, total) + 1):
            j = total - i
            candidates = []
            if i:
                previous = cells[i - 1][j]["states"]
                row = rows[i - 1]
                for parent, node in enumerate(previous):
                    xy = tuple(F(z) for z in node["xy"])
                    nx, ny = _advance(xy, row, 1)
                    candidates.append((nx, ny, i - 1, j, parent, 1))
                    generated += 1
            if j:
                previous = cells[i][j - 1]["states"]
                row = rows[j - 1]
                for parent, node in enumerate(previous):
                    xy = tuple(F(z) for z in node["xy"])
                    nx, ny = _advance(xy, row, 2)
                    candidates.append((nx, ny, i, j - 1, parent, 2))
                    generated += 1
            kept = _pareto(candidates)
            cells[i][j] = {
                "states": [
                    {
                        "xy": [str(z[0]), str(z[1])],
                        "parent_cell": [z[2], z[3]],
                        "parent": z[4],
                        "stream": z[5],
                    }
                    for z in kept
                ],
                "cover1": [],
                "cover2": [],
            }

    # Coverage is stored at the predecessor cell and points into the corresponding
    # successor frontier.  This is generated after all cells exist.
    coverage = 0
    for i in range(m + 1):
        for j in range(m + 1):
            cell = cells[i][j]
            states = [tuple(F(z) for z in node["xy"]) for node in cell["states"]]
            if i < m:
                target = [tuple(F(z) for z in node["xy"]) for node in cells[i + 1][j]["states"]]
                row = rows[i]
                cell["cover1"] = [_dominator(target, _advance(xy, row, 1)) for xy in states]
                coverage += len(states)
            if j < m:
                target = [tuple(F(z) for z in node["xy"]) for node in cells[i][j + 1]["states"]]
                row = rows[j]
                cell["cover2"] = [_dominator(target, _advance(xy, row, 2)) for xy in states]
                coverage += len(states)

    terminal_front = [tuple(F(z) for z in node["xy"]) for node in cells[m][m]["states"]]
    terminal = min(range(len(terminal_front)), key=lambda k: (max(terminal_front[k]), terminal_front[k]))
    word = []
    i = j = m
    index = terminal
    while i or j:
        node = cells[i][j]["states"][index]
        word.append(node["stream"])
        i, j = node["parent_cell"]
        index = node["parent"]
    word.reverse()
    value = max(terminal_front[terminal])
    return {
        "instance_id": obj["id"],
        "grammar": "all-chain-respecting-link-shuffles",
        "cells": cells,
        "terminal": terminal,
        "lower_bound": str(value),
        "upper_bound": str(value),
        "word": word,
        "generated_transitions": generated,
        "coverage_pointers": coverage,
    }
