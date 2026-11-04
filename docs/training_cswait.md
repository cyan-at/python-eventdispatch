# Training with CSWaits

Design notes for the learning surface (`eventdispatch.learning`):
how a trained policy lives next to a dispatch, and how the
composite-semaphore pair — CSWait / CSRelease — becomes a tool
the policy wields itself. Status: the completion machinery is
implemented (TrainingEvent / TrainingDispatch / CompletionLog);
the policy-crafted waits are design, not yet built.

## The policy lives outside the dispatch

SimClockCSBQCVED has no policy slot: it is queue, clock, and
completion heap, and a handwritten rule runs on it unchanged.
Information flows up as completions; actions flow back down as
ordinary serialized queue items. The dispatch never calls the
policy, and the policy never touches the clock or the queue
directly. Between decision points the policy is not running at
all — no thread, no tick, no polling. Its whole life is a
sequence of consultations, which is what makes it *clockless*:
policy inference is called by signalling, never at a regular
rate.

## The signal: finish, the completions field, the harness

Nothing signals at dispatch; dispatch is only scheduling (quote
a duration, schedule the completion). The signal is the
*finish*:

1. `TrainingEvent.finish()` runs the event's outcome model
   (`run_outcome()`) and appends a completion record to the
   blackboard's completions field — a `CompletionLog` the
   dispatch registered at construction: event id, class name,
   dispatch args, start / completion times, quoted duration,
   wake flag, outcome.
2. The harness — the training loop, or the inference process —
   consumes the field by `take()`: block for the next
   completion, drain everything buffered. The field has exactly
   one consumer, so draining on use is its hygiene: the buffer
   never holds more than one decision interval's records.
3. The harness, not the dispatch, decides engagement: a record
   whose wake flag is set is a decision point. The flag is read
   after finish, so an event can set it from its outcome — wake
   on failure, sleep on routine success. Non-waking completions
   still land in the field: accounting sees them, the policy
   never does.

The same finish serves training and inference unchanged. In
training the harness closes the decision interval (the drained
records and the reward ledger settle the interval reward, the
transition joins the batch), samples the policy's next choice,
and enqueues it; backpropagation happens at batch boundaries,
not per wake. In inference there are no transitions and no
gradients, the choice is greedy, and the items go straight onto
the queue. On a wall-clock dispatch the identical contract holds
with the harness as a separate process woken by the completion
signal.

## Time: irregular engagement, one decision point per instant

Completions that share a sim time fire back to back, in dispatch
order (the heap orders by completion time, then dispatch
sequence — seed-reproducible). The harness drains *all* of them
before consulting the policy once: deciding between two finishes
at the same instant would decide on half the facts, then again
on nothing new. Near-ties are two decision points very close
together.

Engagement is therefore irregular by design — bursty when
completions cluster, silent for the duration of one long event.
The spacing is data, not a defect: each trajectory step records
its actual Δt, and returns are computed with real durations.
An episode is a chain of decision points separated by stretches
of pure machinery: a semi-MDP, where each chosen event is an
option with a duration, and the ledger prices the interval.

## CSWaits as policy tools

Historically the pair was hand-placed structure only. The step
this note records: let the policy *set up mechanisms*. Existing
events release tokens by structure, whether or not they were
designed to be composed; a policy-crafted CSWait declares a
conjunction over that traffic — its lefts are a *set*, so arming
one is an AND-join over producers that don't know they're
composed. The learned object is an association between events:
*when those things happen together, this is worth doing.* That
is the first of the program's open questions (thickening an
event vs training an association between events) in its cleanest
form, and the substrate for it is the board the dispatch
populates: rows for in-flight events, armed waits, and the
token vocabulary with its recent releases — the second open
question (variable entity sets) arriving as the first one's
work surface.

Two disciplines come with the tool:

- **Pricing.** Arming must be charged by the ledger, and
  outstanding mechanisms need a capacity budget. Unpriced
  machinery is a reward-hacking surface.
- **Credit.** The arming decision's payoff arrives at the
  firing, through the mechanism, at a time the arming didn't
  fix. Long-horizon credit assignment to the arming choice is
  the research problem, stated plainly.

With in-sim producers, release times are completion times, so a
wait fires at the max of its lefts' completion times —
deterministic, seed-reproducible.

## The router builds the wait

Crafting a CSWait decomposes along the usual proposer / router
split. The proposer decides a mechanism is worth arming — the
when and the what-kind. The router constructs it, and both of
its parts are grounding work:

1. **The lefts**: pointing at token rows on the board and
   selecting a subset. Variable vocabulary, variable set size —
   no fixed-size head can emit that; pointing over live rows is
   the router's output type.
2. **The pending event**: which event, with which args, fires
   when the wait completes — grounded onto rows the same way
   the router grounds any dispatch.

The mechanism's inputs are the router's outputs; before CS the
router grounded choices onto events and frontiers, and CS
extends its candidate world to mechanisms over what is already
in flight.

The one friction: a CSWait's pending event is serialized at arm
time, so the router commits the grounding with the state it has
then; the only fresh datum the mechanism returns is the
completing release's status. Rule: arm with frozen args when the
continuation is fully determined at arm time; when it isn't, arm
the wait as a wake — it fires, the completion record lands in
the field, and the router grounds with a fresh board at that
decision point.

### Before and after

Scenario: *when the current Nav finishes and the battery is
low, go charge.*

**Before (router without CSWaits).** The router only grounds
immediate dispatches; the conjunction has nowhere to live except
the policy's own memory. The policy must be woken at the Nav's
completion (a wake fixed in advance), check the battery itself,
and decide — and if the battery crosses its threshold mid-Nav,
nothing can act until the Nav ends. Every continuation is
re-planned from scratch at each decision point.

**After (router with CSWaits).** At one decision point the
router points at two board rows — the in-flight Nav's completion
token, the battery monitor's threshold token — and arms a wait
over them, with the ChargeEvent pending (or as a bare wake). The
mechanism holds the conjunction; the producers release
independently; the wait fires at the later of the two, even
mid-way through unrelated work; the pending event crosses into
the queue on its own. The policy spent one grounding action and
carries nothing across decision points.

Before, the router grounds choices onto the *present* board.
After, it grounds them onto *future* board states as well — it
connects in time, not just in space.

## What learns, and how it fits

- **VQ (the vocabulary).** Board rows embed and quantize to
  codes — the pointer reads codes; conjunctions are sets of
  tokens. Codes are trained for reconstruction, not decision
  relevance, and stay frozen during policy training (the
  program's settled recipe); two phenomena differing only in
  whether they should wake the policy can share a code, and a
  frozen codebook cannot notice.
- **Architecture (the reading).** Rows are a set: position-free
  set attention (a small transformer encoder over rows, or
  pooled DeepSets) so each candidate is scored in the context
  of the others; the proposer's choice conditions the scoring
  (cross-attention, or FiLM as the cheap form). Inadmissible
  candidates are masked structurally, never learned around.
- **RL (the choosing).** Single picks with dense, local credit
  fit value methods: per-candidate Q, TD updates, argmax at
  inference. Subset construction (a wait's lefts) is joint — two
  tokens that always co-occur are worth one slot, not two — and
  per-candidate values cannot price that; it fits policy
  gradient over an autoregressive pointer (point, mask, point
  again, stop). One shared board-state critic under both: it
  baselines the proposer's REINFORCE, prices armed waits, and
  gives the router's TD head its bootstrap target.
- **The formal frame** for an armed wait plus its pending event
  is an *option* — initiation set, termination condition as a
  token conjunction — except these options create the decision
  points themselves instead of spanning between given ones.

## Policy stacks engaging each other

Nothing above requires one policy. A token vocabulary on a
shared board is a medium, not a wire: one stack's completions
are phenomena another stack has learned to arm waits on. The
battery stack waits on frontier-exhaustion; the mapping stack
waits on charge-complete; neither is the other's subroutine, and
no supervisor is hand-designed — the engagement pattern itself
is learned. The costs: the vocabulary must stay legible across
stacks (per-stack codebooks do not align automatically), and
credit crosses policy boundaries — when your wait wakes me and
my work pays off, whose return was it? CSWaits, seen this way,
are how a policy learns to exercise its own harness against
simulation phenomena — and how different policy stacks learn to
engage each other.
