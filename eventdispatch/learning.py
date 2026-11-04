"""Learning surface of the eventdispatch framework.

Every language implementation of the framework keeps one module like
this one: the pair that learning / training code programs against.

  LearningEvent    -- the Event base class for trainable systems:
                      SimEvent (eventdispatch.sim)
  LearningDispatch -- the Dispatch subclass that runs them:
                      SimClockCSBQCVED (eventdispatch.sim) plus
                      the training contract

Training code imports from here, never from core internals.

Sim-time protocol (the contract LearningEvent subclasses follow):

  dispatch(ed) -> duration in ticks. Scheduling only: quote the
      duration, stash the args. No outcome sampling, no mutation.
  finish(ed)   -> the completion step. Run the outcome model at
      completion time, against fresh state, apply the event's
      effects, and emit the release signal. Events judge what
      happened (local); the dispatch judges what next (global).

A cancelled event never reaches finish(): it never mutates state.
"""
from __future__ import annotations

from eventdispatch.sim import SimClockCSBQCVED, SimEvent


class LearningEvent(SimEvent):
    """Event base class for trainable systems: SimEvent, named for
    the learning surface (see module docstring). The sim-time
    protocol -- dispatch quotes, finish completes, now() reads the
    dispatch clock -- is inherited unchanged."""


class LearningDispatch(SimClockCSBQCVED):
    """Dispatch for trainable systems: SimClockCSBQCVED plus the
    training contract.

    Its training loop steps the world and the clocked iterables
    with the clock, so interrupts land at sim times mid-event, not only
    at completions; interrupting an in-flight event converts it to
    INTERRUPTED at the current clock time with elapsed / progress
    accounting; each completion returns its release to the policy
    loop, and the dispatch signals idle when nothing is in flight.

    Bare for now: the drive loop is not implemented yet.
    """
