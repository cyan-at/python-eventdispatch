"""Learning surface of the eventdispatch framework.

Every language implementation of the framework keeps one module like
this one: the pair that learning / training code programs against.

  LearningEvent    -- the Event base class for trainable systems
  LearningDispatch -- the Dispatch subclass that runs them

Training code imports from here, never from core internals.

Sim-time protocol (the contract LearningEvent subclasses follow):

  dispatch(ed) -> duration in ticks. Scheduling only: quote the
      duration, stash the args. No outcome sampling, no mutation.
  complete(ed) -> run the outcome model at completion time, against
      fresh state; stash (outcome, metrics).
  finish(ed)   -> emit the release signal for the outcome. Events
      judge what happened (local); the dispatch judges what next
      (global).

A cancelled event never reaches complete(): it never mutates state.
"""
from __future__ import annotations

from eventdispatch.common1 import CommonEvent
from eventdispatch.composite_semaphore import CSBQCVED


class LearningEvent(CommonEvent):
    """Event base class for trainable systems (see module docstring)."""

    def dispatch(self, ed, *args, **kwargs):
        raise NotImplementedError(
            "sim-time protocol: quote duration ticks")

    def complete(self, ed, *args, **kwargs):
        raise NotImplementedError(
            "sim-time protocol: run the outcome model")

    def finish(self, ed, *args, **kwargs):
        raise NotImplementedError(
            "sim-time protocol: emit the release signal")


class LearningDispatch(CSBQCVED):
    """Dispatch subclass for trainable systems.

    Runs LearningEvents on a virtual clock inside the library's
    queue dispatch (the bridge seam): an event's quoted duration is
    its completion time, completions land in duration order, and the
    blackboard clock reads the completion time when the outcome
    model runs.

    Bare for now: the seam is not overridden yet.
    """
