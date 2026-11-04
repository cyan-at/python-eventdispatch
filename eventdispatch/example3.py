"""Example 3: shake out the learning surface (learning.py).

One trivial LearningEvent on a LearningDispatch over a Blackboard,
following example1 / example2's shape. Bare for now: construction
only -- the virtual-clock drive loop lands with the bridge seam in
LearningDispatch.
"""
from __future__ import annotations

from eventdispatch.core import Blackboard
from eventdispatch.learning import LearningDispatch, LearningEvent


class WorkEvent(LearningEvent):
    """Trivial event: one tick, always DONE."""

    def dispatch(self, ed, *args, **kwargs):
        return 1

    def complete(self, ed, *args, **kwargs):
        self._pending = ("DONE", {})

    def finish(self, ed, *args, **kwargs):
        outcome, metrics = self._pending
        return {"event": type(self).__name__,
                "outcome": outcome, "metrics": metrics}


def main():
    blackboard = Blackboard()
    ed = LearningDispatch(blackboard, "learning")
    print("learning surface constructs:", type(ed).__name__)


if __name__ == "__main__":
    main()
