"""Learning surface of the eventdispatch framework.

Every language implementation of the framework keeps one module like
this one: the pair that learning / training code programs against.

  TrainingEvent    -- the Event base class for trainable systems:
                      SimEvent (eventdispatch.sim) whose finish()
                      records its completion (below).
  TrainingDispatch -- the Dispatch subclass that runs them:
                      SimClockCSBQCVED (eventdispatch.sim) plus a
                      registered blackboard asset, the completions
                      field (below).

Training code imports from here, never from core internals.

Sim-time protocol (the contract TrainingEvent subclasses follow):

  dispatch(ed) -> duration in the clock's units. Scheduling only:
      quote the duration, stash the args. No outcome sampling, no
      mutation.
  run_outcome(ed) -> the outcome (the release). Called by finish()
      at completion time, against fresh state: run the outcome
      model, apply the event's effects, return what happened.
  finish(ed)   -> the completion step, implemented by the base
      class: it calls run_outcome(), appends the completion record
      to the completions field, and returns the outcome. Subclasses
      override run_outcome(), never finish().

A cancelled event never reaches finish(): it never mutates state.

The completions field (blackboard key COMPLETIONS_KEY) is a
CompletionLog the dispatch registers at construction. Every
TrainingEvent completion lands there, in completion order: event
id, class name, dispatch args, start / completion times, quoted
duration, wake flag, outcome. That log is the signal board's first
area and the harness's whole input: a training or inference loop
consumes it by take() -- block for the next completion, drain
everything that has landed -- and decides from the records; a
record whose wake flag is set is a decision point. Draining on
use is the field's hygiene: it has exactly one consumer, so the
buffer never holds more than one decision interval's records.
The dispatch itself never engages a policy; notification stops
at the field. The wake flag is read after finish() runs, so an
event can set it from its outcome (wake on failure, sleep on
routine success).
"""
from __future__ import annotations

import threading

from eventdispatch.sim import SimClockCSBQCVED, SimEvent

COMPLETIONS_KEY = "training_completions"


class CompletionLog:
    """The completions field: a condition-signalled buffer of
    completion records, in completion order, drained on use.

    Writers append (TrainingEvent.finish, on the dispatch's
    driver thread). The one reader -- the harness -- consumes by
    take(): records leave the buffer as they are read, so the
    buffer stays bounded by one decision interval no matter how
    long the run. snapshot() is a non-consuming peek, for tests
    and diagnostics only; it is not a read path.
    """

    def __init__(self):
        self._records = []
        self._cv = threading.Condition()

    def append(self, record):
        with self._cv:
            self._records.append(record)
            self._cv.notify_all()

    def take(self, timeout=None):
        """Block until at least one record exists, then drain and
        return everything buffered, in completion order. Returns
        [] on timeout."""
        with self._cv:
            if not self._cv.wait_for(lambda: len(self._records) > 0,
                                     timeout):
                return []
            records, self._records = self._records, []
            return records

    @property
    def pending(self):
        """Records buffered right now (not yet taken)."""
        with self._cv:
            return len(self._records)

    def snapshot(self):
        """Everything buffered, as a list copy. Does not drain."""
        with self._cv:
            return list(self._records)


class TrainingEvent(SimEvent):
    """Event base class for trainable systems.

    Inherits the SimEvent time protocol (started_at /
    quoted_duration stamps, now() on the dispatch clock) and adds
    the completion record: finish() runs the subclass's
    run_outcome(), appends the record to the blackboard's
    completions field when the running dispatch registered one,
    and returns the outcome. On a dispatch without the field,
    finish() is SimEvent's completion step with no recording.

    wake: the harness's engagement hint, read after finish() --
    class-level default True; run_outcome() may set self.wake
    per outcome.

    deserialize drops CommonEvent's non-empty-tail check: a
    zero-arg event (an empty tail) is dispatchable from the queue.
    """

    wake = True

    @staticmethod
    def deserialize(ed, blackboard, *args, **kwargs):
        tokens = args[0] if args else []
        return (ed.reserve_event_id(), blackboard), tuple(tokens)

    def run_outcome(self, ed, *args, **kwargs):
        raise NotImplementedError(
            "training protocol: run_outcome() runs the outcome "
            "model at completion and returns the outcome")

    def finish(self, ed, *args, **kwargs):
        outcome = self.run_outcome(ed, *args, **kwargs)
        bb = self.blackboard
        if bb is not None and COMPLETIONS_KEY in bb:
            bb[COMPLETIONS_KEY].append({
                "event_id": self.get_id(),
                "event": type(self).__name__,
                "args": [list(a) if isinstance(a, (list, tuple))
                         else a for a in args],
                "started_at": self.started_at,
                "t": self.now(),
                "duration": self.quoted_duration,
                "wake": bool(self.wake),
                "outcome": outcome,
            })
        return outcome


class TrainingDispatch(SimClockCSBQCVED):
    """Dispatch for trainable systems: SimClockCSBQCVED plus the
    completions field, registered on the blackboard at construction
    under COMPLETIONS_KEY (an existing CompletionLog there is kept).

    Nothing else is added yet: the training loop that steps world
    and iterables, the interrupt-with-accounting path, and policy
    engagement all belong to the harness that reads the field.
    """

    def __init__(self, blackboard, name):
        super(TrainingDispatch, self).__init__(blackboard, name)
        if COMPLETIONS_KEY not in blackboard:
            blackboard[COMPLETIONS_KEY] = CompletionLog()

    @property
    def completions(self) -> CompletionLog:
        return self.blackboard[COMPLETIONS_KEY]


# Backwards-compatible names (the learning surface's first draft).
LearningEvent = TrainingEvent
LearningDispatch = TrainingDispatch
