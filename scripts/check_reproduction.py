#!/usr/bin/env python3
"""Compare a fresh reproduction against retained claim-critical exact evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

NOISY_KEYS = {"cpu_seconds", "elapsed_wall_seconds", "peak_rss_kib"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items() if key not in NOISY_KEYS}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def normalize_accounting(value: Any, report: str, results: Path) -> Any:
    """Convert the two retained v1 counters without changing scientific values."""
    if report.startswith("reproduction-"):
        report = report[len("reproduction-"):]
    if report not in {"unrestricted-grid-validation.json", "unrestricted-baseline.json"}:
        return value
    version = value.get("accounting_version", 1)
    if version not in (1, 2):
        raise ValueError("unsupported unrestricted accounting version")
    certs = results / "campaign" / "certificates"
    names = [case["id"] for case in value["cases"]]
    paired_states = sum(load(certs / (name + ".json"))["transitions"] for name in names)
    if report == "unrestricted-grid-validation.json":
        if version == 1:
            baseline = load(results / "unrestricted-baseline.json")
            fixture, = [case for case in baseline["cases"] if case["id"] == names[0]]
            value["counts"]["search_states"] += paired_states + fixture["generated_transitions"]
            value["counts"]["checker_obligations"] += fixture["checker_obligations"]
    elif version == 1:
        value["paired_search_states"] = paired_states
        value["search_states"] = value["total_generated_transitions"] + paired_states
    elif (value["paired_search_states"] != paired_states
          or value["search_states"] != value["total_generated_transitions"] + paired_states):
        raise ValueError("unrestricted baseline accounting does not match its components")
    value["accounting_version"] = 2
    return value


def require_equal(left: Path, right: Path, *, canonicalize: bool = True) -> None:
    if not left.is_file() or not right.is_file():
        raise ValueError(f"missing comparison input: {left} or {right}")
    if left.suffix == ".json" and right.suffix == ".json":
        a, b = load(left), load(right)
        if canonicalize:
            a, b = canonical(a), canonical(b)
            a = normalize_accounting(a, left.name, left.parent)
            b = normalize_accounting(b, left.name, left.parent)
        if a != b:
            raise ValueError(f"scientific evidence differs: {left} vs {right}")
    elif left.read_bytes() != right.read_bytes():
        raise ValueError(f"generated source differs: {left} vs {right}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--reproduction-root", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--figure-sources", type=Path)
    parser.add_argument("--paired-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/reproduction-comparison.json"))
    args = parser.parse_args()
    results = args.results.resolve()
    reproduced_root = (args.reproduction_root or results).resolve()

    reports = {
        "validation.json": "reproduction-validation.json",
        "source-schemas.json": "reproduction-source-schemas.json",
        "exchange-conditions.json": "reproduction-exchange-conditions.json",
        "pairing-boundary.json": "reproduction-pairing-boundary.json",
        "unrestricted-grid-validation.json": "reproduction-unrestricted-grid-validation.json",
        "unrestricted-baseline.json": "reproduction-unrestricted-baseline.json",
        "pilot.json": "reproduction-pilot.json",
        "bibliography-integrity.json": "reproduction-bibliography-integrity.json",
    }
    if args.paired_only:
        reports = {}
    for retained, reproduced in reports.items():
        require_equal(results / retained, reproduced_root / reproduced)

    retained_cases = results / "host-campaign" / "cases"
    reproduced_cases = (args.campaign or (reproduced_root / "reproduction")) / "cases"
    retained_certs = results / "host-campaign" / "certificates"
    reproduced_certs = (args.campaign or (reproduced_root / "reproduction")) / "certificates"
    names = sorted(path.name for path in retained_cases.glob("*.json"))
    if len(names) != 36 or names != sorted(path.name for path in reproduced_cases.glob("*.json")):
        raise ValueError("paired campaign case set differs")
    exact_case_fields = (
        "id", "group", "source_schema", "rounds", "events", "edge_bound", "value",
        "terminal_frontier", "widths", "checker", "certificate_bytes", "endpoint_bits",
        "state_bits", "oracle", "branch_bound", "heuristics", "counts",
    )
    for name in names:
        retained = load(retained_cases / name)
        reproduced = load(reproduced_cases / name)
        if any(retained[field] != reproduced[field] for field in exact_case_fields):
            raise ValueError(f"paired case evidence differs: {name}")
        require_equal(retained_certs / name, reproduced_certs / name, canonicalize=False)

    if not args.paired_only:
        require_equal(retained_certs / "stress-04.json",
                      reproduced_root / "reproduction-example-certificate.json", canonicalize=False)

    retained_figures = results / "figure-sources"
    reproduced_figures = args.figure_sources or (reproduced_root / "reproduction-figure-sources")
    figure_names = sorted(path.name for path in retained_figures.iterdir() if path.is_file())
    if not figure_names or figure_names != sorted(path.name for path in reproduced_figures.iterdir() if path.is_file()):
        raise ValueError("figure-source file set differs")
    for name in figure_names:
        require_equal(retained_figures / name, reproduced_figures / name, canonicalize=False)

    report = {
        "canonical_reports_equal": len(reports),
        "paired_cases_equal": len(names),
        "paired_certificates_equal": len(names),
        "example_certificate_equal": None if args.paired_only else True,
        "paired_only": args.paired_only,
        "figure_sources_equal": len(figure_names),
        "ignored_measurement_fields": sorted(NOISY_KEYS),
        "accounting_normalization": "two unrestricted v1 reports converted from retained certificate counts",
        "scope": (
            "exact claim-critical reproduction comparison; ignores only explicitly noisy "
            "CPU, wall-time, and peak-RSS measurements"
        ),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"reproduction comparison failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
