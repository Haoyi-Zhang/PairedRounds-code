#!/usr/bin/env python3
"""Offline integrity checks for the frozen manuscript bibliography evidence.

The checker deliberately does not query the network.  It verifies that the standalone
BibTeX snapshot, the manuscript citation-key snapshot, and the per-entry publisher/
archive audit agree exactly; that BibTeX metadata (type, title, venue, year, volume,
issue, and pages) has not drifted; that stable identifiers and official URLs are
well-formed; and that the predeclared literature-coverage quotas are met.  The input
CSV records a dated publisher/stable-record recheck, while this script itself remains
offline.  Full-text interpretation, continuous network revalidation, and peer review
are not claims of this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Set


def parse_bib_entries(text: str) -> Dict[str, Dict[str, str]]:
    """Parse the brace/quote forms used by this frozen BibTeX file.

    The parser is intentionally small but balanced-brace aware.  Unsupported syntax
    fails closed instead of silently skipping metadata.
    """
    entries: Dict[str, Dict[str, str]] = {}
    pos = 0
    while True:
        match = re.search(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[pos:], re.S)
        if match is None:
            break
        entry_type = match.group(1).lower()
        key = match.group(2)
        if key in entries:
            raise ValueError(f"duplicate BibTeX key {key!r}")
        body_start = pos + match.end()
        cursor = body_start
        depth = 1
        while cursor < len(text) and depth:
            if text[cursor] == "{":
                depth += 1
            elif text[cursor] == "}":
                depth -= 1
            cursor += 1
        if depth:
            raise ValueError(f"unclosed BibTeX entry {key!r}")
        body = text[body_start : cursor - 1]
        fields: Dict[str, str] = {"entry_type": entry_type}
        index = 0
        while index < len(body):
            while index < len(body) and (body[index].isspace() or body[index] == ","):
                index += 1
            if index >= len(body):
                break
            field_match = re.match(r"([A-Za-z][\w-]*)\s*=\s*", body[index:])
            if field_match is None:
                raise ValueError(f"unsupported BibTeX syntax in {key!r} near {body[index:index+40]!r}")
            field = field_match.group(1).lower()
            index += field_match.end()
            if index >= len(body):
                raise ValueError(f"missing value for {key!r}:{field}")
            if body[index] == "{":
                index += 1
                value_start = index
                value_depth = 1
                while index < len(body) and value_depth:
                    if body[index] == "{":
                        value_depth += 1
                    elif body[index] == "}":
                        value_depth -= 1
                    index += 1
                if value_depth:
                    raise ValueError(f"unclosed braced value for {key!r}:{field}")
                value = body[value_start : index - 1]
            elif body[index] == '"':
                index += 1
                value_start = index
                while index < len(body):
                    if body[index] == '"' and body[index - 1] != "\\":
                        break
                    index += 1
                if index >= len(body):
                    raise ValueError(f"unclosed quoted value for {key!r}:{field}")
                value = body[value_start:index]
                index += 1
            else:
                value_start = index
                while index < len(body) and body[index] != ",":
                    index += 1
                value = body[value_start:index].strip()
            if field in fields:
                raise ValueError(f"duplicate field {field!r} in {key!r}")
            fields[field] = value.strip()
        entries[key] = fields
        pos = cursor
    if not entries:
        raise ValueError("no BibTeX entries found")
    return entries


def split_tags(value: str) -> Set[str]:
    return {tag.strip() for tag in value.split(";") if tag.strip()}


def require_nonempty(row: Dict[str, str], fields: Iterable[str]) -> None:
    missing = [field for field in fields if not row.get(field, "").strip()]
    if missing:
        raise ValueError(f"{row.get('key', '<unknown>')}: empty fields {missing}")


def expected_venue(entry: Dict[str, str]) -> str:
    return entry.get("journal") or entry.get("booktitle") or entry.get("institution") or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--literature", type=Path, default=Path("literature"))
    parser.add_argument("--output", type=Path, default=Path("results/bibliography-integrity.json"))
    args = parser.parse_args()

    bib_path = args.literature / "references.bib"
    citations_path = args.literature / "main-citations.txt"
    audit_path = args.literature / "bibliography_audit.csv"
    entries = parse_bib_entries(bib_path.read_text(encoding="utf-8"))
    bib_keys = set(entries)
    citation_keys = {
        line.strip()
        for line in citations_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    with audit_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    audit_keys = [row.get("key", "").strip() for row in rows]
    if len(audit_keys) != len(set(audit_keys)):
        raise ValueError("duplicate audit key")
    audit_key_set = set(audit_keys)

    if bib_keys != citation_keys:
        raise ValueError(
            f"BibTeX/citation mismatch: only_bib={sorted(bib_keys-citation_keys)}, "
            f"only_cited={sorted(citation_keys-bib_keys)}"
        )
    if bib_keys != audit_key_set:
        raise ValueError(
            f"BibTeX/audit mismatch: only_bib={sorted(bib_keys-audit_key_set)}, "
            f"only_audit={sorted(audit_key_set-bib_keys)}"
        )
    if len(bib_keys) != 30:
        raise ValueError(f"frozen bibliography count changed: {len(bib_keys)} != 30")

    required_fields = [
        "key",
        "entry_type",
        "title",
        "year",
        "venue",
        "identifier",
        "official_url",
        "role_tags",
        "calibration_status",
        "metadata_check_date",
        "claim_use",
        "live_metadata_status",
        "live_metadata_note",
    ]
    role_counts: Dict[str, int] = {}
    identifiers: Dict[str, str] = {}
    official_urls: Dict[str, str] = {}
    metadata_dates: Set[str] = set()
    live_metadata_rows = 0
    page_range_entries = 0
    for row in rows:
        require_nonempty(row, required_fields)
        key = row["key"].strip()
        entry = entries[key]

        expected_fields = {
            "entry_type": entry["entry_type"],
            "title": entry.get("title", ""),
            "year": entry.get("year", ""),
            "venue": expected_venue(entry),
            "volume": entry.get("volume", ""),
            "number": entry.get("number", ""),
            "pages": entry.get("pages", ""),
        }
        for field, expected in expected_fields.items():
            actual = row.get(field, "").strip()
            if actual != expected:
                raise ValueError(
                    f"{key}: audit/BibTeX mismatch for {field}: {actual!r} != {expected!r}"
                )
        if row.get("pages", "").strip():
            page_range_entries += 1

        year = row["year"].strip()
        if not (len(year) == 4 and year.isdigit() and 1900 <= int(year) <= 2100):
            raise ValueError(f"{key}: invalid year {year!r}")
        metadata_date = row["metadata_check_date"].strip()
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", metadata_date):
            raise ValueError(f"{key}: invalid metadata check date {metadata_date!r}")
        metadata_dates.add(metadata_date)
        if row["live_metadata_status"].strip() != "publisher_or_stable_record_rechecked":
            raise ValueError(f"{key}: live metadata status is not the frozen recheck status")
        live_metadata_rows += 1
        url = row["official_url"].strip()
        if not url.startswith("https://"):
            raise ValueError(f"{key}: non-HTTPS official URL")
        url_id = url.lower()
        if url_id in official_urls:
            raise ValueError(f"duplicate official URL {url!r}: {official_urls[url_id]}, {key}")
        official_urls[url_id] = key

        tags = split_tags(row["role_tags"])
        if not tags:
            raise ValueError(f"{key}: no role tags")
        for tag in tags:
            role_counts[tag] = role_counts.get(tag, 0) + 1

        ident = row["identifier"].strip()
        ident_id = ident.lower()
        if ident_id in identifiers:
            raise ValueError(f"duplicate identifier {ident!r}: {identifiers[ident_id]}, {key}")
        identifiers[ident_id] = key

        doi = entry.get("doi", "").strip()
        if doi:
            if ident_id != doi.lower():
                raise ValueError(f"{key}: identifier does not match BibTeX DOI")
            if url_id != f"https://doi.org/{doi}".lower():
                raise ValueError(f"{key}: official URL does not match BibTeX DOI")
        journal = entry.get("journal", "")
        arxiv_match = re.fullmatch(r"arXiv preprint arXiv:(\d{4}\.\d{4,5})", journal)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            if ident_id != f"arxiv:{arxiv_id}".lower():
                raise ValueError(f"{key}: arXiv identifier mismatch")
            if url_id != f"https://arxiv.org/abs/{arxiv_id}".lower():
                raise ValueError(f"{key}: arXiv official URL mismatch")
        booktitle = entry.get("booktitle", "")
        if "USENIX Symposium" in booktitle:
            if not ident.startswith("USENIX:"):
                raise ValueError(f"{key}: USENIX record lacks a USENIX identifier")
            if not url.startswith("https://www.usenix.org/conference/"):
                raise ValueError(f"{key}: USENIX record lacks an official conference URL")
        if booktitle == "Proceedings of Machine Learning and Systems":
            if not ident.startswith("MLSys:"):
                raise ValueError(f"{key}: PMLSys record lacks an MLSys identifier")
            if not url.startswith("https://proceedings.mlsys.org/paper_files/paper/"):
                raise ValueError(f"{key}: PMLSys record lacks the official proceedings URL")

        if tags & {"closest_tpds", "influential", "adjacent"}:
            if "full_text" not in row["calibration_status"]:
                raise ValueError(f"{key}: quota paper lacks full-text calibration record")

    quotas = {"closest_tpds": 12, "influential": 5, "adjacent": 5}
    for role, minimum in quotas.items():
        if role_counts.get(role, 0) < minimum:
            raise ValueError(f"coverage quota failed for {role}: {role_counts.get(role, 0)} < {minimum}")
    if metadata_dates != {"2026-09-19"}:
        raise ValueError(f"mixed or stale metadata check dates: {sorted(metadata_dates)}")

    # Freeze the corrections most likely to regress silently.  These are offline
    # assertions over the audited snapshot, not network queries.
    if entries["dsc"].get("doi") != "10.1109/71.308533":
        raise ValueError("DSC DOI regressed from the verified IEEE record")
    if entries["parallelizing"].get("pages") != "414--432":
        raise ValueError("parallelizing page range regressed; IEEE PDF ends on page 432")
    pk = entries["parallelkittens"]
    if not (
        pk.get("entry_type") == "inproceedings"
        and pk.get("booktitle") == "Proceedings of Machine Learning and Systems"
        and pk.get("volume") == "8"
        and pk.get("year") == "2026"
    ):
        raise ValueError("ParallelKittens is not frozen to the formal MLSys 2026 record")

    report = {
        "reference_count": len(bib_keys),
        "cited_key_count": len(citation_keys),
        "audit_row_count": len(rows),
        "all_bib_entries_cited": True,
        "all_citations_resolved": True,
        "all_audit_metadata_matches_bibtex": True,
        "entries_with_stable_identifier": len(identifiers),
        "unique_official_urls": len(official_urls),
        "entries_with_page_ranges": page_range_entries,
        "duplicate_identifiers": 0,
        "duplicate_official_urls": 0,
        "coverage_counts": dict(sorted(role_counts.items())),
        "coverage_minima": quotas,
        "metadata_check_date": next(iter(metadata_dates)),
        "live_metadata_rows": live_metadata_rows,
        "frozen_record_repairs": {
            "dsc_doi": "10.1109/71.308533",
            "parallelizing_pages": "414--432",
            "parallelkittens_record": "PMLSys 8 (MLSys 2026)",
        },
        "scope": (
            "offline integrity of the 2026-09-19 publisher/stable-record snapshot and "
            "declared literature-coverage audit; not continuous network revalidation, "
            "peer review, or a guarantee that every interpretation is correct"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"bibliography integrity check failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
