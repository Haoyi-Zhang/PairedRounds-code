# Exact progress-grid baseline for unrestricted link shuffles

## Scope

This post-freeze baseline keeps the same two private compute/transfer chains, positive
upper-endpoint durations, and one nonpreemptive link as the paired model.  It removes
only the round-pairing rule.  A legal link word is therefore any shuffle of
`1^m` and `2^m` that preserves each stream's own transfer order.  The baseline is an
independent specialization of the classical two-job progress-grid idea; it does not
import or modify an upstream implementation.

The result is boundary evidence.  It is not merged into the original 36-case timing
hypotheses and makes no claim about GPUs, arbitrary job shops, or the running time of
a general geometric scheduler.

## Progress-grid state and transitions

Cell `(i,j)` records prefixes that have completed the first `i` transfers of stream 1
and the first `j` transfers of stream 2.  A label `(x,y)` is the completion time of the
latest completed transfer on each stream (zero before that stream has transferred).
Because the shared link is serial, its current availability is `max(x,y)`.

If the next event is stream 1's transfer `i+1`, its private computation is ready at
`x+a_{i+1}` and the transfer finishes at

```
(max(x+a_{i+1}, y)+p_{i+1}, y).
```

The stream-2 transition is symmetrically

```
(x, max(y+b_{j+1}, x)+q_{j+1}).
```

Thus every legal shuffle is a monotone path from `(0,0)` to `(m,m)`, and replaying its
steps gives exactly the earliest event-DAG schedule for that word.

## Dominance lemma

Both transitions are coordinatewise monotone.  Hence if label `u` weakly dominates
label `v` at the same grid cell, applying any common legal suffix to `u` produces a
terminal label that weakly dominates the one produced from `v`.  A dominated label
can therefore be discarded without changing the terminal Pareto frontier or the
minimum of any coordinatewise monotone objective, including makespan.

## Exactness theorem

At each cell, form all one-step images from the retained frontiers of its left and
lower predecessor cells and retain exactly their nondominated subset.  Induction on
`i+j` proves that this subset is the complete reachable Pareto frontier:

1. every retained label has a checked predecessor and is reachable;
2. every reachable predecessor label is dominated by a retained predecessor by the
   induction hypothesis;
3. transition monotonicity preserves that dominance; and
4. the checked coverage pointer identifies a retained target label that dominates
   every branch from every retained predecessor.

The base cell contains only `(0,0)`.  Therefore the terminal cell is the complete
frontier over all chain-respecting link shuffles.  The minimum terminal makespan is a
lower bound because coverage includes every legal word and an upper bound because the
certificate includes a reachable witness word attaining it.

Unlike the paired-round theorem, this finite grid procedure is not claimed to have a
linear-width frontier at arbitrary depth.  The admitted artifact retains at most
100,000 labels and uses at most 12 rounds per stream.

## Independent checking

`src/unrestricted_checker.py` does not import the solver, paired model, or baseline
implementation.  It independently parses the input, recomputes both transitions,
checks each retained state's parent, verifies strict Pareto order, checks every
outgoing coverage pointer, replays the witness word, and confirms equal lower and
upper bounds.  Eight mutation classes must be rejected.

`tests/unrestricted_grid.py` additionally enumerates every shuffle for all 27 frozen
instances of depth at most seven (25,224 words) and compares the complete terminal
frontier, not only the optimum.  All 36 instances are checked by the coverage
certificate.

## Observed boundary result

On the same 36 frozen upper-endpoint inputs, unrestricted shuffling improves three
paired optima (`stress-09`, `stress-20`, and `stress-24`).  The largest observed
relative reduction is `27272/658639`, about 4.14%, on `stress-24`; its exact absolute
reduction is `3896/165`.  These are finite deterministic results, not a population
estimate or a claim that pairing is usually inexpensive.
