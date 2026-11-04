# Training CSWaits: the architecture

Companion to [Training with CSWaits](training_cswait.md). That
page covers the mechanism; this one records *what learns, and
how* — the training architecture for a policy that can arm
CSWaits. Status: design, unproven. The A/B that tests it is a
small join world (concurrent producers, a decaying conjunction
payoff, a distractor decision stream), Phase 0: hand rules with
and without a hand-placed wait first, then the learned A/B with
wait-arming as the single changed variable.

## Split by horizon

The router has two jobs with different credit horizons, and the
long-horizon machinery belongs to only one of them.

1. **Grounding a dispatch** — pick a frontier, ground args.
   Short horizon: the outcome lands within the interval.
2. **Composing a wait** — choose the lefts (a token subset) and
   the pending event. Long horizon: the arming decision's payoff
   arrives at the firing, an unfixed number of decision points
   later.

## Grounding: value methods

Per-candidate Q over the board's rows, TD (Temporal Difference)
updates, argmax at inference. The credit is dense and local, so
bootstrapping beats Monte Carlo on variance and sample
efficiency. Candidates are scored by set attention over rows —
each in the context of the others, position-free — conditioned
on the proposer's code (cross-attention, or FiLM (Feature-wise
Linear Modulation) as the cheap form). Inadmissible candidates
are masked structurally, never learned around.

## Composing: the long-horizon stack

1. **Actor-critic with a board-state critic** — the workhorse.
   Pure REINFORCE (REward Increment = Nonnegative Factor ×
   Offset Reinforcement × Characteristic Eligibility) pays full
   variance across the arming→firing gap; the critic
   bootstraps value across it, over decision points — the
   semi-MDP (semi-Markov Decision Process) value, Δt-aware.
2. **The options frame** — an armed wait is an option whose
   termination condition is the token conjunction. Option-
   critic's advantage-of-initiation is exactly the credit
   question the arming decision poses: *was initiating this,
   here, worth it?* The router's construction is the option's
   content; the proposer's arm-or-not is its initiation policy.
3. **Subset construction by policy gradient** — the lefts are
   chosen by an autoregressive pointer (point, mask, point
   again, stop-token). A subset's value is joint — two tokens
   that always co-occur are worth one slot, not two — and
   per-candidate values cannot price that complementarity;
   sequential pointing can, each pick conditioned on the ones
   before it.
4. **Transformer as representation, not the learner** — over
   board history and outstanding waits, attention represents
   armed waits' partial progress and gives actor and critic a
   direct path from arming context to firing outcome. Not
   return-conditioned sequence modeling as the training method:
   in this program's v5 history the Decision Transformer was a
   cloning technique off a teacher, with no pure-RL evidence
   behind it, and the program's direction is RL-first.

## The prescription

Set-attention to read; autoregressive pointer to compose;
bootstrapped critic to span the gap; options semantics to
define what "worth arming" means; TD values for the local
picks. One shared board-state critic under both router jobs: it
baselines the proposer's REINFORCE, prices armed waits, and
gives the TD head its bootstrap target. Each piece is matched
to the structure it actually faces — the long-horizon tools go
exactly where the horizon is, and nowhere else.

## Relation to the existing stacks

This is a departure, not a description. The routers in the
program today are trained three other ways, none of them with
an RL signal of their own: arm1's router is a deterministic
expander (untrained); v6_door's router is distilled from CEM
(Cross-Entropy Method) search labels, with pure-RL parity
proven separately in Phase 6; the mapping stacks train proposer
and router jointly with REINFORCE, so grounding credit arrives
only through the whole action's return. What the proposer hands
the router in all of them is a decision in abstract space — a
code (the door stack's StateVQ code, as FiLM conditioning), or a
kind (the mapping stack's EXPLORE / CHARGE) — never concrete
args. Under this architecture the hand-off is unchanged; what
changes is that the router's own picks get their own training
signals, split by horizon as above.
