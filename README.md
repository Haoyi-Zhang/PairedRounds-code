# Max-plus timing certificates

This standalone repository studies exact timing frontiers for **two private
compute/transfer chains sharing one nonpreemptive communication link**.  Its main
theorem assumes *paired rounds*: both transfers of round `k` precede both transfers
of round `k+1`, while each stream may resume its private computation as soon as its
own transfer completes.  This is a mathematical and CPU-only artifact, not a GPU
scheduler, trace study, or device benchmark.

For `m` paired rounds, the full nondominated frontier after round `k` has at most
`k+1` states; a positive rational family attains the bound at every depth.  The
solver propagates the exact frontier in quadratic total exact-arithmetic work and
emits local reachability and all-branch coverage witnesses.  A separately
implemented checker reconstructs four-event DAG transitions and verifies matching
lower and upper makespan bounds.  The ordinary mathematical proofs are in
`proofs/paired-rounds.md`; they are not a mechanized proof of Python.

A second, post-freeze boundary baseline removes only the pairing rule.  It uses an
exact progress grid over all shuffles of `1^m` and `2^m`, with an independent
checker and a complete small-instance shuffle oracle.  This baseline quantifies the
scope restriction; it does not establish a linear frontier bound for unrestricted
interleavings.  Its proof and trust boundary are in `proofs/unrestricted-grid.md`.

## Requirements

Use Python 3.10 or later on Linux with only the standard library.  No installation,
network access, GPU, model API, external solver, parent directory, or paper source is
required.  Each scientific command uses one worker and enforces the artifact's
300-second and 3-GiB process limits.

## Exact reproduction

Run these commands from the repository root.  Every command writes to a
`reproduction-*` path, so retained evidence remains unchanged.  The entry points
disable Python bytecode emission before importing local modules; after the run the
repository-integrity check therefore remains meaningful without manual cache cleanup.

```sh
python tests/validation.py results/reproduction-validation.json
python scripts/check_source_schemas.py --output results/reproduction-source-schemas.json
python tests/exchange_conditions.py results/reproduction-exchange-conditions.json
python tests/pairing_boundary.py results/reproduction-pairing-boundary.json
python tests/unrestricted_grid.py results/reproduction-unrestricted-grid-validation.json
python scripts/run_unrestricted_baseline.py results/reproduction-unrestricted-baseline.json
python scripts/run_campaign.py --output results/reproduction
python scripts/compare_results.py results/campaign results/reproduction
python scripts/solve.py inputs/stress-04.json results/reproduction-example-certificate.json
python scripts/check_certificate.py inputs/stress-04.json results/reproduction-example-certificate.json
python scripts/check_bibliography.py --output results/reproduction-bibliography-integrity.json
python scripts/pilot.py --output results/reproduction-pilot.json
python scripts/export_paper_data.py --output results/reproduction-figure-sources
python scripts/check_reproduction.py
python scripts/check_repository_integrity.py --output results/reproduction-repository-integrity.json
```

`scripts/check_reproduction.py` compares all exact claim-critical report fields, all
36 paired case records and certificates, the example certificate, bibliography
integrity result, and all generated paper-data sources.  It ignores only the three
explicitly noisy measurement fields: process CPU time, elapsed wall time, and peak
RSS.  `scripts/check_repository_integrity.py` excludes its own output file from its
static scan, so repeated execution has stable scope.

To test resume behavior, rerun the campaign command with `--resume`; every reused
case certificate is checked, and the extra checks are charged in that output
directory.  `scripts/compare_results.py` deliberately does not require noisy
wall-clock samples to match.


## Retained evidence

`inputs/` contains 36 exact frozen inputs generated with seed `20260915`.  Twelve
are source-inspired abstract schemas: three declared macro motifs at depths 2, 4,
6, and 8.  They are not twelve published workloads or extracted traces.  The other
24 inputs are six synthetic stress families at depths 3, 5, 7, and 12.  Every
duration is synthetic.  `source_schemas/` and `proofs/source-boundary.md` state the
conditional event mapping and excluded semantics.  The schema checker is not a CUDA
extractor, memory-model proof, or hardware test.

For paired rounds, all 36 complete terminal frontiers agree with full enumeration
of 26,604 legal words.  The certificates retain 505 nodes and cover 840 branch
transitions.  The sharp 12-round case has frontier width 13 and optimum 157.  A
two-round negative control has exact optimum 14 but value 15 after scalar-prefix
pruning.  Validation also contains 5,103 pair-map attacks, 56 independently seeded
tiny instances, 1,024 interval-corner evaluations, 144 fixed-upper interval
perturbations, 18 malformed input/certificate classes, and 6,875 contextual
exchange checks.

For unrestricted link shuffles, all 36 progress-grid certificates pass.  A separate
oracle enumerates all 25,224 shuffles for the 27 cases of depth at most seven and
agrees on every complete terminal frontier.  The grid retains 8,195 labels and
14,015 transitions across the collection; its largest cell frontier has 24 labels.
Removing pairing improves exactly three frozen optima: `stress-09` (115 to 113),
`stress-20` (358 to 356), and `stress-24` (`658639/1155` to `57397/105`).  The
largest relative reduction is `27272/658639`, about 4.14%.  Eight grid-certificate
mutation classes are rejected.  A separate transparent two-round example has paired
optimum 17 and unrestricted optimum 13.

Per-call implementation costs use monotonic elapsed wall time; aggregate process CPU
is used only for campaign accounting.  The first timing attempt suffered coarse
process-clock quantization, including zero single-call samples.  Those raw
observations remain in `results/coarse-clock-observation.json` but are not interpreted
as zero-cost executions.  Sorting propagation and branch-and-bound are often faster
than the merge solver on these small cases, so no fastest-solver claim is made.

## Trust boundary

Inputs admit 1--12 rounds, exactly resources `C1`, `C2`, and `L`, no additional
precedence constraints, nonnegative interval lower endpoints, and positive upper
endpoints.  Endpoint numerators and denominators are each limited to 64 bits;
stored exact completion coordinates allow 3,200 bits.  JSON readers reject duplicate
keys, non-finite values, unsupported fields, oversized files, and malformed numeric
encodings.  Invalid or over-cap inputs fail; the artifact does not convert an
interrupted computation into an exact claim.

The paired checker imports neither the paired optimizer nor its skyline code.  The
unrestricted checker imports neither grid solver nor paired implementation.  Both
still trust Python, exact rational arithmetic, and the declared event semantics.  A
second implementation is not independent peer review or formal verification.
Certificate acceptance proves optimality only inside the corresponding grammar and
independent duration box.  Correlated uncertainty, multicast, shared atomic targets,
multiple links, three streams, overlap-dependent durations, and raw CUDA semantics
are outside scope.

The sorting DP, branch-and-bound, and priority rules are transparent baselines for
the paired grammar, not renamed reproductions of HEFT, CPOP, DCP, or a general
two-job geometric solver.  Classical two-job scheduling already has broader
polynomial algorithms.  This artifact claims a tight stage-frontier theorem and
checkable coverage consequence for its paired subfamily, plus an exact boundary
comparison to all shuffles.

## Repository map and status

- `src/`: paired and unrestricted solvers, independent checkers, model, baselines,
  input generation, resource limits, and I/O contracts.
- `tests/`: finite proof attacks, mutation tests, exact tiny oracles, and negative
  controls.
- `scripts/`: campaign, reproduction comparison, certificate tools, source-schema
  check, boundary baseline, pilot, and paper-data export.
- `proofs/`: ordinary proofs and explicit model/source boundaries.
- `results/`: retained exact inputs, certificates, raw repetitions, validation,
  clean-reproduction report, and cumulative resource accounting.
- `claim_evidence_ledger.csv`: material claims mapped to proofs, checkers, tests,
  tables, and raw evidence.
- `external_resources.csv`: scholarly/official sources, access mode, and
  redistribution boundary.
- `literature/`: the frozen 30-entry manuscript bibliography, citation-key snapshot,
  and per-entry metadata/claim audit. The audit records a dated 19 September 2026
  publisher/stable-record recheck, including the corrected DSC DOI and the formal
  MLSys 2026 ParallelKittens record while preserving the exact arXiv v1 source-reading
  boundary. Run `python scripts/check_bibliography.py` to verify exact key coverage,
  duplicate identifiers, frozen metadata, and the 14-TPDS / 5-influential /
  6-adjacent quotas offline; this integrity check is not a network or peer review.

`results/reproduction-report.json` records the final fresh standalone extraction, and
`results/reproduction-comparison.json` is the machine-generated exact-field comparison.
`results/resource-accounting.json` freezes the original campaign, validation, repairs,
unrestricted boundary work, and its designated clean repetition. Its counters retain
their original measurement scope; `counter_corrections` gives the two unrestricted
all-call counts derived from the saved certificates. Current entry points include
those calls. The reproduction comparator translates these two old counter schemas
before comparing; it does not ignore changed scientific results. A later duplicate
review replay is disclosed separately in `results/post-handoff-audit.json`; it changed
no scientific input or result and is not used to obscure the original campaign ceiling.
None of these records is a submission decision, external review, or hardware
validation.
