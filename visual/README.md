# VisUAL: linked-list visualizer

VisUAL is an optional feature integrated into Lau-PyDE. Use **Run → Run VisUAL (Linked List)** or `Ctrl+Shift+R`. Normal **Run File** and `Ctrl+R` continue to use the existing Python runner.

## Initial contract

The first version recognizes top-level `Node` and `LinkedList` classes, with `Node.data`, `Node.next`, and `LinkedList.head`. It interprets supported source in a separate worker process and produces immutable snapshots for step navigation.

Supported constructs include simple class/method definitions, local and supported field assignments, `None`, booleans, integers and strings, `if`/`else`, `while`, comparisons, simple arithmetic, method calls defined in the program, `return`, `break`, and `print()`. Imports, dynamic execution, reflection, recursion, unsupported statements/expressions, and arbitrary file/network access are rejected.

This is a deliberately controlled subset, not a general-purpose Python visualizer or a universal security sandbox. A trace is generated only when the analyzer accepts the complete source.

## Intent detection

VisUAL uses explainable AST-based signals before validation. `from dsa import LinkedList` is only a weak hint and never opens VisUAL by itself. Strong intent requires a conventional `Node` (`data` and `next`), a conventional `LinkedList` (`head`), and actual list construction. Node/list definitions without meaningful use are reported as possible intent. The analyzer also reports evidence and diagnostics separately, so strong intent cannot bypass the controlled-subset validator. The specific `dsa` hint import is accepted as a non-executing import; other imports remain unsupported.

## Tests

From the repository root:

```bash
python -m pytest -q
```

The tests cover conventional detection, unsupported syntax, recursion, trace generation, duplicate node identities, step limits, insertion, deletion, updating, and source structure.
