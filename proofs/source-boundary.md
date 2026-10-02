# Source-to-model boundary

Source: S. H. Sul, S. Arora, B. F. Spector and C. Ré, *ParallelKittens:
Systematic and Practical Simplification of Multi-GPU AI Kernels*, Proceedings of
Machine Learning and Systems, vol. 8 (MLSys 2026). The byline lists those four
authors in that order. This document attributes a public technical source; it does
not assert collaboration, endorsement, or authorship of this project.

The exact substantive version read for model intake was arXiv:2511.13940v1,
submitted 17 November 2025: https://arxiv.org/abs/2511.13940,
https://arxiv.org/html/2511.13940v1, and https://arxiv.org/pdf/2511.13940. The
formal publication record was rechecked on 19 September 2026 at
https://proceedings.mlsys.org/paper_files/paper/2026/hash/ff997469ac66cf893c4183efeb22212a-Abstract-Conference.html.
The substantive v1 source was inspected, including its primitive table,
transfer/scheduling discussion, measurements, and Appendix D pseudocode. No upstream
code or figure is copied into this repository. Neither the arXiv distribution route
nor the proceedings page is treated as permission to redistribute the full paper here.

## What the source actually supplies
The paper presents eight primitives and a unified kernel template, evaluated on
Hopper and Blackwell. Its template distinguishes loader, consumer, storer and
communicator roles. Loader waits for input-buffer reuse and issues asynchronous
loads. Consumer waits for arrival, performs matrix computation, waits for its
completion, and releases inputs. Storer waits for output production, issues an
asynchronous store and waits for the source-read phase before releasing the
output buffer. Dedicated communication work may run on different SMs.

These are useful event/synchronization motifs, not a proof that all of the source's
kernels have the graph or resource model studied here. In particular, a
source-read wait is NOT a general destination-visibility guarantee. A relaxed-load
spin wait is not, by itself, a formal memory-ordering proof. All-reduce, multicast,
several simultaneous links, shared atomic targets, and variable resource contention
are outside the admitted grammar. No hardware timing or speedup transfers from the
source paper to our measurements.

## Three restricted abstract motifs

| Motif | Source anchor | Own abstract interpretation | Extra assumptions / restriction |
|---|---|---|---|
| producer-store | Appendix D consumer/storer; outputs-arrived and output reuse | Local completed production is C; completed point-to-point transfer is T | T ends only at the completion/visibility required by the next event, not at launch or source-read completion. Private buffers, one admitted link and paired link rounds are imposed. |
| load-consumer-reuse | Appendix D loader/consumer; input arrival and reuse | Cut a tile cycle after a completed load: C consumes the current tile; T completely loads the next tile | Single-buffer conservative reuse; computation of the next admitted item follows the full T completion. Initial tile availability is assumed. No claim of equivalence to the multibuffer original template. |
| dedicated-communicator | Dedicated communication role, separate from local computation | Two private producer chains submit complete point-to-point transfers to one serial service resource | Only an abstract single-link service actor is retained. The source's collective and multi-device communication are not serialized and claimed equivalent. |

There are twelve depth-unrolled schemas (three motifs at depths 2,4,6,8), not twelve
independent published workloads. All numerical durations are synthetic and recorded
as such. The schema JSON files are newly authored declarations of the restricted
model. They do not contain extracted CUDA instructions or measured traces.

## Conditional mapping argument
Assume the admitted macro contract: every C uses only its private computation
resource; every T holds the link for its whole nonpreemptive duration and completes
all data/notification effects required by its successor; each chain has a private
buffer; initial data are ready; no external dependencies exist; durations are
fixed with respect to the selected overlap; and the link enforces paired rounds.

Map each macro event one-to-one to C(i,k) or T(i,k). The local production/arrival
and reuse requirements yield C(i,k)->T(i,k)->C(i,k+1). Consecutive events in the
selected link word yield its resource edges. These are all admitted dependencies.
The private-resource conflicts are already ordered by the chains; all link
conflicts are ordered by the link word. Therefore the resulting event graph is
exactly the mathematical graph, and its longest paths are a sound earliest-time
interpretation of THIS macro contract. An implementation satisfying only some of
these assumptions is not admitted by this argument. Adding a conservative wait
may yield a feasible restricted policy without preserving the unrestricted
implementation's optimum.

## Executable scope
`scripts/check_source_schemas.py` generates the twelve explicit event/resource
schemas from the frozen source-inspired inputs, validates every admitted field and
edge, and enumerates all legal link words for acyclicity. It also rejects removal of
a chain dependency, introduction of a cross-stream compute wait, use of a third
compute resource, launch-only completion, a collective target, and non-paired link
policy. This checks the internal abstraction, NOT the source's CUDA memory model,
not a compiler extraction, and not a device execution. The source interpretation
above remains an ordinary explicitly conditional argument.
