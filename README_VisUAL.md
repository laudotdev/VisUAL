# VisUAL

**VisUAL is an educational program-visualization project designed to make data structures and algorithms easier to understand by showing how a program changes as it executes.**

Instead of asking learners to imagine what happens behind each line of code, VisUAL aims to make those changes visible: the objects a program creates, the references that connect them, the values that change, and the sequence of operations that leads to a result.

VisUAL began as a linked-list visualization tool integrated into **Lau-PyDE**. Its direction is broader: build a clear, step-by-step learning experience for understanding data structures, algorithms, and the underlying behavior of a program.

---

## The Problem VisUAL Addresses

Learning a data structure is not only about memorizing its operations or getting the expected output. The difficult part is often understanding *what happens in memory while the code runs*.

For example, when a linked list inserts a node, a learner may see the final list but still be unsure about:

- Which node was created?
- What does `head` refer to before and after the operation?
- Which node's `next` reference changed?
- Did a node's value change, or did a reference change?
- In what order did the statements execute?
- How did one small assignment transform the structure?

Traditional diagrams usually show a structure at a single point in time. Source code shows the instructions, while program output shows the result. The connection between those views can be difficult to follow—especially when references, object identity, loops, and mutations are involved.

**VisUAL is intended to connect these pieces together.** It makes execution a sequence of inspectable states, helping learners relate source code to the actual changes taking place in a program.

## What Is VisUAL?

VisUAL is a step-by-step educational visualizer for understanding program execution, with a focus on data structures and algorithms.

Its planned experience brings together two complementary views:

1. **General object and memory view** — a way to inspect variables, objects, values, identities, and references as the program runs.
2. **Specialized data-structure visualizations** — purpose-built views that make a particular structure or algorithm easier to understand, rather than representing everything as generic boxes and arrows.

The goal is to show not only *what the structure looks like*, but also *why it looks that way at the current step*.

### A step should explain what actually happened

A useful visualization should do more than announce that an event occurred. An explanation such as “value updated” is incomplete unless the learner can identify which object's value changed and what it changed from and to.

VisUAL's intended step explanations should connect the event to the relevant source line and program state. For example, a value-update step should make clear:

- which object or node was affected;
- which attribute was changed;
- the previous value and the new value, when applicable;
- which variables or references point to the affected object; and
- how the operation changes the visible data structure.

The exact details depend on the operation. The principle is consistent: **explain the change in terms a learner can follow, not just in terms of an internal event name.**

## Design Philosophy

VisUAL is being shaped around a few core principles.

### 1. Make execution understandable

The visualization should answer the learner's natural questions: *What just happened? Why did it happen? What changed? What stays the same?*

Technical event names may be useful for implementation and debugging, but the learner-facing explanation should describe the actual operation and its effect.

### 2. Keep code and visualization connected

The current source line, step explanation, relevant variables, object/reference view, and program output should complement one another. Each view provides a different piece of the same execution story.

### 3. Show identity and references, not just values

Two objects can contain the same value without being the same object. A variable stores or refers to something; an object attribute can refer to another object; and changing a reference is different from changing the value inside an object.

VisUAL should preserve these distinctions so learners can understand object identity, aliasing, and links between objects instead of seeing only a simplified final diagram.

### 4. Use both general and specialized views

A general memory/object view helps explain common program behavior across different examples. Specialized visualizations can then present a data structure in the form that best communicates its operations.

Neither view should replace the other. The aim is a shared execution model with visual representations suited to the concept being taught.

### 5. Make stepping reliable

Moving backward and forward through an execution should let learners inspect recorded states without accidentally running the program again and changing the result. A step history should represent what happened during the original execution, with stable object identities across the recorded states.

### 6. Be explicit about limitations

A trustworthy educational tool should not invent a visualization when it cannot accurately interpret a program. VisUAL's execution support is intentionally defined by a supported language contract. Unsupported constructs should produce understandable diagnostics rather than misleading diagrams.

### 7. Prefer clarity over visual noise

The interface should help learners focus on the current operation and the relationship between code and state. Explanations, labels, references, and controls should be organized around the learning task—not presented as a wall of technical information.

## How a VisUAL Session Should Work

A typical learning session is intended to follow this cycle:

1. **Read the code.** Identify the operation the program is about to perform.
2. **Run the visualization.** VisUAL records the supported program's execution as a sequence of states.
3. **Inspect a step.** Follow the current source line and its explanation.
4. **Examine the state.** Check relevant variables, objects, values, and references.
5. **Move through the history.** Use the previous and next controls to compare how the program changes over time.
6. **Connect the change to the concept.** Relate the visible state to the data-structure operation or algorithm being studied.

The purpose is not merely to animate code. It is to give learners time and evidence to reason about execution.

## VisUAL and Lau-PyDE

VisUAL's story began inside **Lau-PyDE**, a lightweight Python development environment created to keep the everyday coding workflow simple. The first VisUAL experience focused on conventional singly linked lists and helped connect Python source code with nodes, `head`, `next` references, traversal, insertion, deletion, and value updates.

That starting point established the central idea: learners should be able to step through an execution and see how the structure changes, rather than relying on the final output alone.

Lau-PyDE is the environment in which VisUAL originated. **VisUAL is the educational visualization project and its own learning-focused identity.** Its long-term direction is not limited to a single linked-list diagram. The plan is to build on the original experience with a more general object-and-memory model, specialized data-structure visualizations, and explanations that describe each step in understandable terms.

This distinction matters: Lau-PyDE provides a place to write and run Python programs, while VisUAL focuses on helping learners understand what those programs do.

## Execution Accuracy and Supported Scope

VisUAL prioritizes an accurate explanation of the execution it supports over pretending to understand every possible Python program.

The initial implementation is centered on a controlled subset of Python suitable for conventional singly linked-list examples. The broader architecture being planned combines a general object/memory representation with specialized data-structure views.

This means VisUAL should be understood as an educational execution visualizer—not as a replacement for the full Python runtime, a general-purpose debugger, or a promise that arbitrary Python syntax can be visualized.

When a program uses syntax or behavior outside the supported contract, VisUAL should report the limitation clearly. A clear explanation of what is unsupported is more useful than a visualization that looks plausible but is wrong.

## Project Direction

VisUAL's development is guided by one main question:

> **Can a learner understand what the program changed, why it changed, and how that change affects the data structure—one step at a time?**

The planned direction includes:

- clearer, operation-specific step explanations;
- a consistent representation of objects, values, identities, and references;
- a general object/memory view that can support more than one data structure;
- specialized visualizations for data structures and algorithms;
- reliable step history with stable identities across recorded states;
- source-aware diagnostics for unsupported constructs; and
- a focused interface that makes execution easier to reason about.

These are design goals and architectural direction, not a claim that every capability is already implemented.

## The Meaning of VisUAL

VisUAL represents the project's focus on **visual understanding**: turning the invisible process of program execution into something learners can inspect, question, and reason about.

The ambition is simple: help learners move beyond knowing that code works to understanding **how and why it works**.

---

## Origin

VisUAL originated as part of [Lau-PyDE](https://github.com/laudotdev/Lau-PyDE_open-source), an open-source Python development environment.

VisUAL's scope, interface, and implementation continue to evolve around its educational purpose: making program execution and data structures easier to understand through accurate, step-by-step visualization.
