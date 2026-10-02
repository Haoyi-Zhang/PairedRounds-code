# Complete mathematical argument

This is a mathematical proof in ordinary notation, not a mechanized proof. Python
programs separately check finite instances. The independently implemented checker is
not an independent scientific review. Durations below are positive rational upper
endpoints; the algebra extends to positive real durations.

## 1. Event semantics and exact transition

For each i in {1,2}, the precedence chain is
C(i,1), T(i,1), C(i,2), T(i,2), ..., C(i,m), T(i,m).
C events use a private unary resource; T events use one common unary link. All
transfers of round k precede every transfer of round k+1. Within a round the link
order is 12 or 21. No edge requires the next private computation to wait for the
other stream's transfer. No preemption, duration dependence on overlap, extra
release constraints, or hidden buffer-sharing constraints are admitted.

Every binary order word gives an acyclic graph: every chain/link edge has
nondecreasing round index, and the only within-round link edge is one directed edge
between the two transfers. The compute-to-transfer edges cannot complete a cycle.
Earliest starts are the longest-path evaluation of that DAG and minimize all event
completion times for this fixed order. The graph has 4m events, 4m-2 base edges and
at most 2m-1 additional consecutive-link edges. The precedence-only graph consists
of two parallel chains. The resource-augmented DAG need not be series-parallel.

At the end of round k-1 let x and y be the two transfer completion times. The link
is available at max(x,y), while private computations are released at x and y.
Writing the current durations as (a,b,p,q), the exact maps are

    T12(x,y) = (u, max(y+b,u)+q),  u = max(x+a,y)+p;
    T21(x,y) = (max(x+a,v)+p, v),  v = max(y+b,x)+q.

In the first equation x+a >= x absorbs the link release x; likewise b >= 0 for the
second. The link release of the other stream is not discarded. These equations are
also obtained by evaluating four local event nodes, which is the checker's route.

In max-plus notation (matrix product takes row maxima of coefficient plus input),

    M12 = [[a+p,       p],
           [a+p+q, max(b,p)+q]],
    M21 = [[max(a,q)+p, b+q+p],
           [q,          b+q]].

## 2. Intervals and dominance

Every fixed-order DAG completion time is a maximum of path sums with nonnegative
coefficients in event durations. It is componentwise nondecreasing. For independent
closed intervals the vector of upper endpoints belongs to the uncertainty set and
therefore attains the worst completion time for every fixed order. Minimizing these
worst cases is exactly the deterministic upper-endpoint order problem. This is a
standard monotonicity reduction, not a new robust-optimization theorem.

All transition maps are componentwise monotone. If s <= t coordinatewise, every
fixed legal suffix maps s to a vector <= the image of t. Thus a reachable state t
can be discarded when a reachable s <= t exists. Only upper-endpoint dominance is
needed to preserve the minimax optimum. This does not assert that an upper-endpoint
dominator is uniformly better at every other duration realization.

Let F_0={(0,0)} and

    F_k = Min( T12_k(F_(k-1)) union T21_k(F_(k-1)) ),

where Min removes coordinatewise dominated distinct points. Every finite strict
antichain in two coordinates can be listed x_1<...<x_N and y_1>...>y_N.

## 3. Orientation lemma

Let M=[[alpha,beta],[gamma,delta]] satisfy
alpha+delta >= beta+gamma. For s=(x,y), t=(x',y') with x<x', y>y', if Ms and Mt are
incomparable then (Ms)_1 < (Mt)_1 and (Ms)_2 > (Mt)_2.

Proof. The only alternative incomparable orientation has (Ms)_1 > (Mt)_1 and
(Ms)_2 < (Mt)_2. The first strict inequality forces

    y+beta > x'+alpha,

because the x summand is smaller for s. The second forces

    x'+gamma > y+delta,

because the y summand is smaller for t. Together these imply

    delta-gamma < x'-y < beta-alpha,

contradicting delta-gamma >= beta-alpha. Equality in an output coordinate cannot
be incomparability, so these are all possibilities. QED.

Both scheduling matrices satisfy the diagonal-advantage condition: the respective
advantages are max(b,p)-p and max(a,q)-q, both nonnegative.

## 4. Disjoint survival lemma

No two distinct incomparable input vectors remain incomparable under both T12 and
T21 for the same positive (a,b,p,q).

Proof. Order the inputs as in Section 3 and suppose both image pairs are
incomparable. By the orientation lemma, the second coordinate of T12(s) exceeds
that of T12(t). Since x<x', that inequality requires

    y + max(b,p)+q > x' + a+p+q,
    x'-y < H := max(b,p)-a-p.

The first coordinate of T21(s) is less than that of T21(t). Since y>y', that requires

    x' + max(a,q)+p > y + b+q+p,
    x'-y > J := b+q-max(a,q).

But

    J-H = min(a,q)+min(b,p) > 0.

Thus x'-y cannot be both smaller than H and greater than J. QED. Positivity is used
for this strict gap; nonnegative durations still give J>=H and the two strict
necessary inequalities remain incompatible. The delivered theorem and admissible
upper-endpoint input family use positive durations, avoiding unneeded degenerate
cases in other statements.

## 5. Tight frontier bound

Theorem. For any finite strict input antichain F of N states,

    |Min(T12(F) union T21(F))| <= N+1.

Consequently |F_k| <= k+1 for every number of rounds k.

Proof. In each branch independently, retain its strict Pareto frontier and choose
one input representative for each distinct retained image. Call the two sets of
input representatives A and B. Distinct representatives in one set have distinct,
incomparable images. If A intersection B contained two distinct inputs, their images
would be incomparable in both branches, contrary to Section 4. Hence |A intersection
B|<=1, and

    |A|+|B| = |A union B| + |A intersection B| <= N+1.

Cross-branch pruning cannot increase that sum. Starting from |F_0|=1 proves the
inductive bound. Equal branch images are handled by choosing just one representative;
no assumption of injectivity was made. QED.

## 6. Sharp positive rational family

For all m>=1 set the first round to (1,1,1,1). For k>=2 define

    d_k = 2^(-(k-1)),
    (a_k,b_k,p_k,q_k) = (2k-3+2d_k, 2k-1+d_k, 1, 1).

Then |F_k|=k+1 for every k. The minimum makespan is k(k+1)+1. The family uses
O(k+log k) bits per endpoint, so its width is not purchased through exponential
input description length.

Proof. At k=1, F_1={(2,3),(3,2)}. For the induction, suppose the preceding antichain
has its rightmost point (X,Y) with X-Y=1, final y-gap g>0, and minimum coordinate
difference D=min_i(x_i-y_i). Choose

    d=g/2, a=1-D, b=a+2-d, p=q=1.

In this construction 0<d<=1/2 and a>=1. For every input, x_i-y_i>=D=1-a, so the
first coordinate of T12 is x_i+a+1. For every input except the last,

    x_i-y_i < 1-g < 1-d=b-a-1,

where the first inequality follows from x_i<X and y_i>=Y+g. Its second coordinate
is therefore y_i+b+1. For the last input, difference 1>1-d makes the second
coordinate X+a+2. The first N-1 images retain their strict antichain order. The
second-coordinate gap between the penultimate and last image is g-d>0. Thus T12
retains all N inputs, with rightmost output P=(X+a+1,X+a+2).

For T21, every input has x_i-y_i<=1, so y_i+b>=x_i and y_i+b+1>=x_i+a. Therefore

    T21(x_i,y_i)=(y_i+b+2,y_i+b+1).

The last input, which has the smallest y_i, dominates all other images. Its image
Q=(Y+b+2,Y+b+1) satisfies

    Q_1-P_1 = 2-d > 0,      P_2-Q_2 = d > 0.

It is incomparable with P and lies to the right and below all earlier T12 outputs.
Exactly N+1 states survive. Their last gap is d and their rightmost coordinate
difference remains 1. The new minimum difference is D-2+d.

Starting with g=1,D=-1 yields g_k=d_k and
D_k=2-2k-d_k, which gives precisely the announced a_k,b_k. In addition the last two
states are

    P_k=(k(k+1), k(k+1)+1),
    Q_k=(k(k+1)+2-d_k, k(k+1)+1-d_k).

For k=1 this agrees with the base case, using d_1=1. Substitution in the displayed
transition formulas proves the coordinate identities inductively. All preceding
states have second coordinate greater than P_k's; Q_k has maximum at least
k(k+1)+1, with equality only at k=1. Hence the optimum is k(k+1)+1. QED.

## 7. Linear merge and arithmetic complexity

For one branch write its first output as max(x_i+A,y_i+B). Since x_i increases and
y_i decreases, the predicate x_i+A>=y_i+B has one split point. Before that point,
first outputs follow y_i+B and strictly decrease. After it they follow x_i+A and
strictly increase. Reversing the first arm and merging with the second gives
lexicographically sorted image points in O(N) work. Strictness of the input means
no ties within an arm; a usual tuple merge handles cross-arm ties.

Merge the two branch streams, sorted by (x,y,parent,order), and scan left-to-right.
Retain a point exactly when its y is strictly smaller than the last retained y.
Every discarded point has a retained predecessor with no larger x or y. For equal
x, sorting by y places the unique potentially minimal image first. The scan thus
returns exactly the full skyline and, without a separate search, one dominator index
for every emitted candidate. Parent and branch of a retained point provide its
reachability witness.

At round k there are at most k inputs and 2k candidates. The total candidate count
is at most m(m+1); the retained state count, including the root, is at most
1+m(m+3)/2. Arithmetic-operation complexity is O(m^2), online frontier memory O(m),
and a certificate retaining all layers is O(m^2) rational coordinates and indices.
The artifact stores the full certificate and therefore uses O(m^2), not O(m), space.

A completion is a path sum of at most n=4m rationals. If numerator and denominator
of each endpoint have at most B bits, an unreduced common-denominator representation
has denominator at most nB bits and numerator at most nB+ceil(log2 n)+1 bits.
Reduction only decreases those bounds. This is a polynomial bit bound, not unit-cost
64-bit arithmetic: comparison and Fraction reduction operate on larger temporary
integers. At n<=48 and B<=64 the stored-coordinate bound is below 3200 bits; temporary
cross products may be approximately twice that width. The checker admits 3200-bit
stored values and uses arbitrary-precision rational arithmetic.

## 8. Certificate soundness and completeness

A certificate contains a layer of retained states per round. Every retained state
has an earlier-layer parent and its 12/21 decision. For every retained input in the
preceding layer, both decision branches name a same-layer dominator. It also contains
an incumbent order word and claimed matching bounds.

The checker independently constructs and evaluates the four-event DAG for all
reachability and coverage obligations. It verifies the initial state, grammar,
interval limits, retained-state reachability, coordinatewise domination of every
branch, strict antichains, indices, round count, final minimum, and replay of the
incumbent. It imports none of the optimizer's transition or pruning implementation.
It does trust ordinary Python arithmetic/control flow and the stated input contract.

Inductive invariant: every state reachable by any legal prefix is coordinatewise
at least one retained state in the corresponding layer. At round zero this is
immediate. Let t be reachable at round k from t' using branch b. By the invariant
there is retained s'<=t'. Monotonicity gives Tb(s')<=Tb(t')=t. Explicit coverage
provides a retained s<=Tb(s'), hence s<=t. Each retained state is itself reachable
because its parent and transition were separately checked.

At the final layer L=min_{s retained} max(s) is <= the makespan of every legal order
by the invariant. It is also attained by a reachable retained state. The replayed
incumbent supplies a feasible upper bound U=L. Thus the accepted value is the exact
optimum over the admitted paired-round grammar and, by Section 2, its independent-box
minimax optimum. The checker does not infer exactness from merely finding a good
feasible schedule or replaying its critical path.

Completeness for valid inputs: take the exact propagated frontiers, select one parent
per retained image, and for each branch select any retained image dominating it. Such
a dominator exists by finite Pareto minimization. All checks succeed. Sections 5 and
7 bound the necessary certificate size. The delivered implementation does not attempt
partial/unknown certificates; a cap or validation failure returns failure, not a
false exact-optimality claim.

## 9. Reset characterization and universal-exchange boundary

For T12, u=max(x+a,y)+p and v=max(y+b,u)+q. If b<=p, then y+b<=u and v-u=q for every
entry. Conversely, if b>p, sufficiently x-dominant entries have gap q, while
sufficiently y-dominant entries have gap b-p+q>q. Thus the output lag is independent
of the entry exactly when b<=p. Symmetrically T21 has u-v=p for every entry exactly
when a<=q. If both conditions hold in every round, each branch produces a totally
ordered image, so the union frontier has at most two states at every round. The
one-round (1,1,1,1) example attains two. This is a reset subfamily, not the assumption
behind the general k+1 bound.

Neither branch uniformly coordinatewise dominates the other for strictly positive
durations and arbitrary entry states. M12's lower-left entry exceeds M21's by a+p;
M21's upper-right entry exceeds M12's by b+q. Making the respective input coordinate
dominate exposes each violation. This only rules out a universal coordinatewise
exchange direction, not contextual or objective-specific exchange principles.

## 10. Counterexamples delimiting the result

Scalar greedy: rounds (2,1,1,2),(10,1,1,1). First-round states are (3,5) for 12 and
(4,3) for 21. Current makespan prefers 21, yet 12 then 21 attains 14 while the best
continuation after 21 is 15. Retaining the smaller prefix maximum is unsound.

Dimension alone: at step k, max-plus diagonal maps add either (2^k,0) or (0,2^k).
After m steps all 2^m resulting vectors are distinct and have equal coordinate sum,
hence are pairwise incomparable. Off-diagonal entries here are minus infinity.
These are not the complementary scheduling matrices; the result does not extend
merely because a different system has two coordinates.

Correlated uncertainty: one round has a=b=1 and p,q in [1,2] constrained by p+q=3.
For either link order the true worst makespan is 4, while the infeasible all-upper
corner gives 5. The box reduction cannot identify that correlated-set optimum.

Source abstractions: a read-completion signal need not mean remote visibility;
concurrent multicast or atomic reduction need not be a unary link event. These are
model-admission failures, not phenomena our scheduling proof establishes. No theorem
here certifies a raw GPU kernel or proves optimality over unrestricted link shuffles.

## 11. Exact contextual exchange conditions

For a fixed entry (x,y), put z=x-y. With strictly positive a,b,p,q,

    T12(x,y) <= T21(x,y) iff b>=p and z<=b-a-p,
    T21(x,y) <= T12(x,y) iff a>=q and z>=b+q-a.

All comparisons are coordinatewise. Otherwise the two images are incomparable.
These statements concern a single input difference z, not the cross-input quantity
x'-y in the pair-survival lemma. They do not assert one universal order.

Proof. Translation equivariance permits y=0,x=z. Write

    u=max(z+a,0)+p,       v=max(b,u)+q,
    v'=max(b,z)+q,        u'=max(z+a,v')+p.

Since v'>0 and u>z, u<=u' and v>=v'. The first pair dominates the second exactly
when v=v'. Because u>z, this is equivalent to b>=u, or jointly b>=p and
z<=b-a-p. Under this condition u'=b+q+p>u. Conversely the second pair dominates
exactly when u=u'. Since v'>0, this is equivalent to z+a>=v', or jointly a>=q
and z>=b+q-a. Then v>v'. The two dominance regions cannot overlap: their z
thresholds differ by p+q>0. QED.

The solver still emits both branches; the theorem is not reported as an implemented
short-circuit speed improvement. The separate finite check enumerates 6,875 exact
single-entry cases using the independently implemented event-DAG transition. It was
added after the frozen campaign and is not a performance-case selection criterion.

## 12. Exact-frontier recovery and terminal deadline queries

The certificate invariant proves more than one objective value. At every layer,
the checked strict antichain S equals the entire nondominated reachable set F.
Indeed, for t in F, coverage supplies a reachable s in S with s<=t. Minimality
forces s=t. Conversely, if retained t were dominated by a different reachable r,
coverage of r would give retained s<=r<t, contradicting S being an antichain.
Thus S=F; this reasoning uses both reachability and coverage, not just either one.

For terminal coordinate deadlines (D1,D2), a fixed word meets both for every
duration realization in the independent box iff some final retained state s
satisfies s1<=D1 and s2<=D2. Necessity follows by considering the admissible upper
corner and covering its completion vector. Sufficiency follows from reachability
of s at the upper corner and coordinatewise duration monotonicity for that word.
The first-round/second-round scalar counterexample has terminal frontier
{(14,7),(15,5)}. Deadlines (14,5) are infeasible jointly even though each coordinate
minimum satisfies its own deadline; (14,7) and (15,5) are separately feasible.
The same full-frontier argument applies to any fixed coordinatewise nondecreasing
terminal objective. This is a standard consequence of Pareto completeness, not a
new theorem about arbitrary intermediate deadlines, energy or hardware costs.

## 13. Pairing is a genuine restriction

For two rounds (a,b,p,q)=(1,10,1,1),(1,1,5,1), all chain-respecting link words and
their earliest makespans are

    1122:13, 1212:17, 1221:18, 2112:19, 2121:18, 2211:20.

Digits identify streams; successive occurrences use that stream's successive
transfers. Only 1212,1221,2112,2121 obey pairing, so the paired optimum is 17.
For unrestricted 1122 the transfer finishes are 2,8,11,13. Stream 2's own chain
has length 10+1+1+1=13, proving unrestricted optimality without trusting an oracle.
The complete six traces and paired certificate are retained in
results/pairing-boundary.json. This separately labeled post-freeze illustration
shows that an accepted paired optimum need not be the unrestricted optimum.
