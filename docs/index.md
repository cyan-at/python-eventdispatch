# [python-eventdispatch](https://github.com/cyan-at/python-eventdispatch)

**eventdispatch** is a Python package for solving the *discrete time synchronization problem* in any computer system. It consists of:

1. A **core** python module, containing the following classes:
    1. **[Blackboard](classes.md#blackboard)**, a thread safe dictionary
    2. **[EventThread](classes.md#eventthread)**, a thread subclass
    3. **[Event](classes.md#event)**, the abstract base class to override
        * Your use case can be decomposed down to `EventDispatch` and `Event` child classes
    4. **[EventDispatch](classes.md#eventdispatch)**, which defines core mechanism functions
    5. Various other decorators, helper functions
2. A **common1** python module, with:
    1. **[BlackboardQueueCVED](classes.md#blackboardqueuecved)**, a example Dispatch subclass that ties the above together
        * You are encouraged to subclass and override or create your own `EventDispatch` child class
    2. A `CommonEvent` class, with some useful, but not necessary logic
    3. Various other decorators, helper functions
3. [0.2.\*] A **composite_semaphore** python module, with:
    1. **[CompositeSemaphore](classes.md#compositesemaphore)**, a <a href="https://en.wikipedia.org/wiki/Semaphore_(programming)">semaphore</a> that supports multiple 'left's and 'right's
    2. **[CSWait](classes.md#cswait)**, an Event subclass that registers a CompositeSemaphore on some tokens (comma-separated strs) and some Event serializations on the right 
    3. **[CSRelease](classes.md#csrelease)**, an Event subclass that produces some tokens to possibly unblock some CSWaits.
        * Combined with CSWait, this pair allows **volatility**, on-the-fly associations between Events as opposed to an Event type hardcoding what to dispatch next in its **finish** definition
    4. **[CSBQCVED](classes.md#csbqcved)**, a BlackboardQueueCVED subclass that enforces CSWait ordering, **necessary** if one wants to use CS* mechanisms


4. A **sim** python module, for running a dispatch on a *simulated clock* (simulation, testing, training):
    1. **[SimEvent](classes.md#simevent)**, an Event base class whose `dispatch` *quotes a duration* instead of occupying a thread, and whose `finish` is the completion step
    2. **[SimClockCSBQCVED](classes.md#simclockcsbqcved)**, a CSBQCVED whose dispatch schedules completions on the simulated clock and fires them in duration order: deterministic, faster than real time, no EventThreads. Engine adapters (MuJoCo, PyBullet, handwritten sims) override only `step_world`
5. A **learning** python module, the surface learning / training code programs against:
    1. **[TrainingEvent](classes.md#trainingevent)**, SimEvent whose finish records its completion on the board's completions field
    2. **[TrainingDispatch](classes.md#trainingdispatch)**, SimClockCSBQCVED plus the completions field and clock settling at finish
    3. Design notes: **[Training with CSWaits](training_cswait.md)** — decision points, the completions field, and CSWaits as tools the policy crafts itself; **[Training CSWaits: the architecture](training_cswait_arch.md)** — what learns, and how, split by credit horizon

Example programs, runnable after installing:

1. <a href="https://github.com/cyan-at/python-eventdispatch/blob/main/eventdispatch/example_core.py" target="_blank">example_core</a>, the core mechanism on a BlackboardQueueCVED: `eventdispatch_example_core`
2. <a href="https://github.com/cyan-at/python-eventdispatch/blob/main/eventdispatch/example_cs.py" target="_blank">example_cs</a>, the CSWait / CSRelease mechanism on a CSBQCVED: `eventdispatch_example_cs`
3. <a href="https://github.com/cyan-at/python-eventdispatch/blob/main/eventdispatch/composite_semaphore.py" target="_blank">cs_main</a>, the CompositeSemaphore produce / consume demo: `eventdispatch_cs_main`
4. <a href="https://github.com/cyan-at/python-eventdispatch/blob/main/eventdispatch/example_sim_mujoco.py" target="_blank">example_sim_mujoco</a>, SimClockCSBQCVED stood up against MuJoCo: `eventdispatch_example_sim_mujoco` (requires `mujoco`)

---

<a href="https://pypi.org/project/eventdispatch/#files" target="_blank">Install via pip</a>

```bash
virtualenv try-eventdispatch
. try-eventdispatch/bin/activate
pip install eventdispatch
```

<a href="https://index.ros.org/r/ros2_eventdispatch/" target="_blank">Install via ROS2-(>=Jazzy) APT</a>

```bash
sudo apt-get install -y ros-jazzy-eventdispatch-python
sudo apt-get install -y ros-jazzy-eventdispatch-ros2-interfaces
sudo apt-get install -y ros-jazzy-eventdispatch-ros2
```

---

* EventDispatch is based on the idea that **what happens defines what happens *next***. Independently derived, the idea is a mirror of <a href="https://en.wikipedia.org/wiki/Markov_chain">Markov chains</a>.
    * EventDispatch frames *all computer programs as <a href="https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Arnold_representation_theorem">superpositioned</a> Markov processes*.
    * Control is about *inducing* and then *injecting synthetic steering* into **superpositioned Markov transitions**.

* Other synchronization architectures exist such as <a href="https://en.wikipedia.org/wiki/Behavior_tree_(artificial_intelligence,_robotics_and_control)" target="_blank">behavior trees</a> and <a href="https://en.wikipedia.org/wiki/Finite-state_machine" target="_blank">state machines</a>.
    * Compared to those architectures, **eventdispatch** is *thin*, *scalable*, inherently *concurrent*.
        * The number of events active in memory in a system using **EventDispatch** is theoretically limited by the CPU's thread limit.
        * The number of **Events** *defined/declared/dispatchable* in such a system theoretically limited by the machine's runtime memory limit.
        * *Dispatch* is a **verb**, not a **noun**. Within a system, more than one component can *dispatch events*.
        * **Events** do not impose any meta-language on the practioner, within the 3 interface functions you are free to write in the *native* language. It remains trivial to express complex behaviours.

* EventDispatch is a mechanism from robotics. However, it is relevant to any system that faces *volatility* in what is asked of it (the right), and *uncertainty* in what it asks of others (the left).  See [Usage patterns & best practices](usage.md).

---

The **EventDispatch** mechanism can be extended to a variety of *messaging mechanisms* in their respective packages, their documentations listed here:

1. ROS2 (WIP)

---

For any new messaging mechanism integrations or use case ideas, <a href="mailto:cyanatg@gmail.com">email me!</a>