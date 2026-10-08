#!/usr/bin/env python3
"""Static, offline repository-integrity checks for the standalone artifact."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple


def reject_duplicate_pairs(pairs: Sequence[Tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def iter_files(
    root: Path, suffixes: Iterable[str], exclude: Iterable[Path] = ()
) -> List[Path]:
    allowed = set(suffixes)
    excluded = {p.resolve() for p in exclude}
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix in allowed and p.resolve() not in excluded
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("results/repository-integrity.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.output if args.output.is_absolute() else root / args.output
    out = out.resolve()

    required = [
        "README.md", "LICENSE", "src/model.py", "src/solver.py", "src/checker.py",
        "src/unrestricted_grid.py", "src/unrestricted_checker.py",
        "tests/validation.py", "tests/unrestricted_grid.py",
        "scripts/run_campaign.py", "scripts/check_bibliography.py",
        "scripts/check_reproduction.py",
        "proofs/paired-rounds.md", "proofs/unrestricted-grid.md",
        "claim_evidence_ledger.csv", "external_resources.csv",
        "literature/references.bib", "literature/main-citations.txt",
        "literature/bibliography_audit.csv",
    ]
    missing = [rel for rel in required if not (root / rel).is_file()]
    if missing:
        raise ValueError(f"missing required files: {missing}")

    symlinks = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_symlink())
    archives = sorted(
        str(p.relative_to(root)) for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z"}
    )
    caches = sorted(
        str(p.relative_to(root)) for p in root.rglob("*")
        if p.name == "__pycache__" or p.suffix in {".pyc", ".pyo"}
    )
    if symlinks or archives or caches:
        raise ValueError(f"disallowed filesystem entries: symlinks={symlinks}, archives={archives}, caches={caches}")

    py_files = iter_files(root, {".py"})
    local_modules = {p.stem for p in (root / "src").glob("*.py")}
    local_modules |= {p.stem for p in (root / "tests").glob("*.py")}
    local_modules |= {"src", "scripts", "tests"}
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    unresolved_imports: list[tuple[str, str]] = []
    syntax_checked = 0
    banned_matches: list[tuple[str, str]] = []
    banned = re.compile(r"TODO|FIXME|TBD|PLACEHOLDER|/mnt/data|anonymous\.4open|example\.com")
    for path in py_files:
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            raise ValueError(f"syntax error in {path.relative_to(root)}: {exc}") from exc
        syntax_checked += 1
        if path.name != "check_repository_integrity.py":
            match = banned.search(text)
            if match:
                banned_matches.append((str(path.relative_to(root)), match.group(0)))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            for name in names:
                if not name or name == "__future__":
                    continue
                if name not in stdlib and name not in local_modules:
                    unresolved_imports.append((str(path.relative_to(root)), name))
    if unresolved_imports or banned_matches:
        raise ValueError(f"source scan failed: unresolved={unresolved_imports}, banned={banned_matches}")

    json_files = iter_files(root, {".json"}, {out})
    for path in json_files:
        with path.open(encoding="utf-8") as handle:
            json.load(handle, object_pairs_hook=reject_duplicate_pairs)

    csv_files = iter_files(root, {".csv"})
    csv_rows = 0
    for path in csv_files:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            raise ValueError(f"empty CSV file: {path.relative_to(root)}")
        width = len(rows[0])
        if width == 0 or any(len(row) != width for row in rows):
            raise ValueError(f"ragged CSV file: {path.relative_to(root)}")
        csv_rows += max(0, len(rows) - 1)

    max_file = max(
        (p.stat().st_size, str(p.relative_to(root)))
        for p in root.rglob("*") if p.is_file() and p.resolve() != out
    )
    report = {
        "required_files": len(required),
        "python_files_syntax_checked": syntax_checked,
        "unresolved_imports": 0,
        "json_files_parsed_with_duplicate_key_rejection": len(json_files),
        "csv_files_rectangular": len(csv_files),
        "csv_data_rows": csv_rows,
        "symlinks": 0,
        "nested_archives": 0,
        "cache_entries": 0,
        "largest_file_bytes": max_file[0],
        "largest_file": max_file[1],
        "scope": (
            "static/offline repository integrity; complements but does not replace mathematical proofs, "
            "dynamic tests, dependency security review, or formal verification"
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"repository integrity check failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
