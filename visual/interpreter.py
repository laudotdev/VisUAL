"""A small, explicit AST interpreter for VisUAL.

It intentionally does not use Python eval/exec. Only AST forms validated by
``visual.analyzer`` are interpreted. It is designed for education, not as a
universal security sandbox.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any

from .analyzer import analyze_source
from .trace import freeze_snapshot


@dataclass
class ExecutionResult:
    status: str
    snapshots: list[dict] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    error: str | None = None


class _Instance:
    def __init__(self, class_name: str, identity: int):
        self.class_name = class_name
        self.identity = identity
        self.attrs: dict[str, Any] = {}


class _Missing:
    pass


_MISSING = _Missing()


@dataclass
class _Method:
    owner: _Instance
    function: ast.FunctionDef


class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


class _StepLimit(Exception):
    pass


class ControlledInterpreter:
    """Execute a validated linked-list program and produce immutable snapshots."""

    def __init__(self, max_steps: int = 5000, max_snapshots: int = 5000):
        self.max_steps = max_steps
        self.max_snapshots = max_snapshots
        self._reset()

    def _reset(self) -> None:
        self.tree = None
        self.classes: dict[str, ast.ClassDef] = {}
        self.globals: dict[str, Any] = {}
        self.frames: list[dict[str, Any]] = []
        self.instances: list[_Instance] = []
        self.next_identity = 1
        self.snapshots: list[dict] = []
        self.output: list[str] = []
        self.steps = 0
        self.status = "running"
        self.error: str | None = None
        self.source = ""
        self.output_characters = 0
        self.max_output_characters = 1_000_000
        self.max_string_characters = 100_000
        self.max_integer_bits = 4096
        self._traversed_node_ref: int | None = None
        self._pending_explanation: str | None = None

    def run(self, source: str) -> ExecutionResult:
        self._reset()
        self.source = source
        # The UI requires the dsa import before launching VisUAL. Keeping the
        # interpreter permissive preserves direct interpreter/test usage for
        # structural linked-list programs.
        analysis = analyze_source(source, require_dsa_import=False)
        if not analysis.supported:
            message = "\n".join(
                f"Line {item.line}, column {item.column}: {item.message}"
                for item in analysis.diagnostics
            ) or "Program is not supported by VisUAL."
            return ExecutionResult("failed", [], [], message)
        try:
            self.tree = ast.parse(source)
            self.classes = {
                item.name: item for item in self.tree.body if isinstance(item, ast.ClassDef)
            }
            # Class/function declarations are registered before top-level execution.
            for item in self.tree.body:
                if isinstance(item, ast.ClassDef):
                    self._record(item, "class_definition", self._class_explanation(item))
                elif isinstance(item, ast.FunctionDef):
                    self.globals[item.name] = item
                elif isinstance(item, ast.ImportFrom) and item.module == "dsa" and any(
                    alias.name == "LinkedList" for alias in item.names
                ):
                    # The import is an intent marker; the controlled
                    # interpreter uses the user's own LinkedList definition.
                    continue
                else:
                    self._exec_stmt(item)
            self.status = "completed"
            self._record(None, "completed", "Program completed successfully.")
        except _StepLimit:
            self.status = "failed"
            self.error = f"Execution step limit reached ({self.max_steps}). Check for an infinite loop."
            self._record(None, "failed", self.error, force=True)
        except Exception as exc:
            self.status = "failed"
            self.error = str(exc) or type(exc).__name__
            self._record(None, "failed", f"Execution failed: {self.error}", force=True)
        return ExecutionResult(self.status, self.snapshots, self.output, self.error)

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise _StepLimit()

    def _locals(self) -> dict[str, Any]:
        return self.frames[-1] if self.frames else self.globals

    def _exec_block(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self._exec_stmt(statement)

    def _exec_stmt(self, node: ast.stmt) -> None:
        self._tick()
        event = "statement"
        explanation = f"Executed {type(node).__name__}."
        if isinstance(node, ast.ClassDef):
            event, explanation = "class_definition", self._class_explanation(node)
        elif isinstance(node, ast.FunctionDef):
            self._locals()[node.name] = node
            event, explanation = "function_definition", f"Defined method {node.name}()."
        elif isinstance(node, ast.Assign):
            value = self._eval(node.value)
            for target in node.targets:
                self._assign(target, value)
            event, explanation = self._assignment_event(node, value)
            explanation = self._pending_explanation or explanation
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id in self.classes:
                event = "object_creation"
                explanation = f"Created a {node.value.func.id} object from the class blueprint."
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                value = self._eval(node.value)
                self._assign(node.target, value)
                event, explanation = self._assignment_event(node, value)
                explanation = self._pending_explanation or explanation
        elif isinstance(node, ast.AugAssign):
            old = self._eval(node.target)
            right = self._eval(node.value)
            value = self._apply_binop(node.op, old, right)
            self._assign(node.target, value)
            event, explanation = "assignment", "Updated a variable or field using an augmented assignment."
        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                values = [self._eval(arg) for arg in node.value.args]
                self._traversed_node_ref = self._node_reference_from_print(node.value)
                emitted = " ".join(str(self._display_value(value)) for value in values)
                self._append_output(emitted)
                event, explanation = "output", f"Printed {emitted!r} to Program Output."
            else:
                self._eval(node.value)
                event, explanation = "expression", "Evaluated an expression or method call."
        elif isinstance(node, ast.If):
            condition = bool(self._eval(node.test))
            expression = ast.unparse(node.test)
            branch = "the if branch" if condition else "the else branch"
            event, explanation = "condition", f"Condition `{expression}` evaluated to {condition}; execution follows {branch}."
            self._record(node, event, explanation)
            self._exec_block(node.body if condition else node.orelse)
            return
        elif isinstance(node, ast.While):
            iteration = 0
            while bool(self._eval(node.test)):
                self._tick()
                iteration += 1
                self._record(node, "condition", f"Condition `{ast.unparse(node.test)}` evaluated to True; while-loop iteration {iteration} runs.")
                try:
                    self._exec_block(node.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            else:
                self._record(node, "condition", f"Condition `{ast.unparse(node.test)}` evaluated to False; the while-loop finished.")
            return
        elif isinstance(node, ast.Return):
            value = self._eval(node.value) if node.value else None
            self._record(node, "return", f"Returned {self._describe_value(value)} from the current method.")
            raise _ReturnSignal(value)
        elif isinstance(node, ast.Break):
            raise _BreakSignal()
        elif isinstance(node, ast.Continue):
            raise _ContinueSignal()
        elif isinstance(node, ast.Pass):
            event, explanation = "statement", "Passed without changing program state."
        else:
            raise RuntimeError(f"Unsupported statement: {type(node).__name__}")
        self._record(node, event, explanation)

    def _assignment_event(self, node: ast.AST, value: Any) -> tuple[str, str]:
        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            targets = [getattr(node, "target", None)]
        fields = [target.attr for target in targets if isinstance(target, ast.Attribute)]
        if "data" in fields:
            return "value_update", "Updated a node's data value."
        if "next" in fields:
            return "link_change", "Changed a node's next reference."
        if "head" in fields:
            return "link_change", "Changed the linked list's head reference."
        if any(isinstance(target, ast.Name) for target in targets):
            return "assignment", "Assigned a value or reference to a variable."
        return "assignment", "Updated a value or reference."

    def _assign(self, target: ast.expr, value: Any) -> None:
        if isinstance(target, ast.Name):
            previous = self._locals().get(target.id, _MISSING)
            self._locals()[target.id] = value
            self._pending_explanation = f"Variable `{target.id}` changed from {self._describe_value(previous)} to {self._describe_value(value)}."
        elif isinstance(target, ast.Attribute):
            owner = self._eval(target.value)
            if not isinstance(owner, _Instance):
                raise RuntimeError("Only supported object fields can be assigned.")
            if target.attr.startswith("__"):
                raise RuntimeError("Dunder attributes are not supported.")
            previous = owner.attrs.get(target.attr, _MISSING)
            owner.attrs[target.attr] = value
            self._pending_explanation = self._reference_explanation(owner, target.attr, value, previous)
        elif isinstance(target, (ast.Tuple, ast.List)):
            if not isinstance(value, (tuple, list)) or len(value) != len(target.elts):
                raise RuntimeError("Unpacking assignment shape mismatch.")
            for subtarget, subvalue in zip(target.elts, value):
                self._assign(subtarget, subvalue)
        else:
            raise RuntimeError(f"Unsupported assignment target: {type(target).__name__}")

    def _eval(self, node: ast.AST | None) -> Any:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and len(node.value) > self.max_string_characters:
                raise RuntimeError("String literal exceeds VisUAL's size limit.")
            if isinstance(node.value, int) and node.value.bit_length() > self.max_integer_bits:
                raise RuntimeError("Integer literal exceeds VisUAL's size limit.")
            if isinstance(node.value, (str, int, bool, type(None))):
                return node.value
            raise RuntimeError("Unsupported literal type.")
        if isinstance(node, ast.Name):
            if node.id in self._locals():
                return self._locals()[node.id]
            if node.id in self.globals:
                return self.globals[node.id]
            if node.id == "None":
                return None
            if node.id == "True":
                return True
            if node.id == "False":
                return False
            raise RuntimeError(f"Unknown name '{node.id}'.")
        if isinstance(node, ast.Attribute):
            owner = self._eval(node.value)
            if not isinstance(owner, _Instance):
                raise RuntimeError("Attribute access is limited to VisUAL-managed objects.")
            if node.attr.startswith("__"):
                raise RuntimeError("Dunder attributes are not supported.")
            if node.attr in owner.attrs:
                return owner.attrs[node.attr]
            method = self._find_method(owner.class_name, node.attr)
            if method is not None:
                return _Method(owner, method)
            raise RuntimeError(f"Object of type {owner.class_name} has no supported attribute '{node.attr}'.")
        if isinstance(node, ast.Call):
            args = [self._eval(arg) for arg in node.args]
            if node.keywords:
                raise RuntimeError("Keyword arguments are not supported by VisUAL yet.")
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name == "print":
                    self.output.append(" ".join(str(self._display_value(value)) for value in args))
                    return None
                if name in self.classes:
                    return self._construct(name, args)
                if name in {"int", "str", "bool"} and len(args) == 1:
                    return {"int": int, "str": str, "bool": bool}[name](args[0])
                raise RuntimeError(f"Call to '{name}()' is not supported by VisUAL.")
            function = self._eval(node.func)
            if isinstance(function, _Method):
                call_text = ast.unparse(node)
                parameters = [arg.arg for arg in function.function.args.args]
                frame = {"self": function.owner}
                frame.update(zip(parameters[1:] if parameters and parameters[0] == "self" else parameters, args))
                self.frames.append(frame)
                try:
                    self._record(node, "method_call", self._method_call_explanation(function, args, call_text))
                finally:
                    self.frames.pop()
                return self._call_method(function.owner, function.function, args)
            raise RuntimeError("Only supported user-defined methods and built-ins can be called.")
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator)
                if not self._compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BinOp):
            return self._apply_binop(node.op, self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp):
            value = self._eval(node.operand)
            if isinstance(node.op, ast.Not): return not value
            if isinstance(node.op, ast.USub): return -value
            if isinstance(node.op, ast.UAdd): return +value
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for item in node.values:
                    result = self._eval(item)
                    if not result: return result
                return result
            if isinstance(node.op, ast.Or):
                result = False
                for item in node.values:
                    result = self._eval(item)
                    if result: return result
                return result
        if isinstance(node, ast.IfExp):
            return self._eval(node.body if self._eval(node.test) else node.orelse)
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(self._eval(item) for item in node.elts) if isinstance(node, ast.Tuple) else [self._eval(item) for item in node.elts]
        if isinstance(node, ast.Subscript):
            value, index = self._eval(node.value), self._eval(node.slice)
            if isinstance(value, (tuple, list, str)) and isinstance(index, int):
                return value[index]
            raise RuntimeError("Subscript access is supported only for literal sequences.")
        raise RuntimeError(f"Unsupported expression: {type(node).__name__}")

    def _construct(self, class_name: str, args: list[Any]) -> _Instance:
        instance = _Instance(class_name, self.next_identity)
        self.next_identity += 1
        self.instances.append(instance)
        init = self._find_method(class_name, "__init__")
        if init is not None:
            self._call_method(instance, init, args)
        return instance

    @staticmethod
    def _class_explanation(node: ast.ClassDef) -> str:
        fields = []
        for function in node.body:
            if isinstance(function, ast.FunctionDef) and function.name == "__init__":
                fields.extend(target.attr for statement in function.body if isinstance(statement, ast.Assign)
                              for target in statement.targets if isinstance(target, ast.Attribute) and target.value.id == "self")
        detail = "; ".join(f"{field}: an attribute of each object" for field in dict.fromkeys(fields))
        return f"Defined class {node.name} as a blueprint for creating objects." + (f" It describes {detail}." if detail else "")

    def _method_call_explanation(self, method: _Method, args: list[Any], call_text: str) -> str:
        parameters = [arg.arg for arg in method.function.args.args]
        pairs = [f"self refers to the {method.owner.class_name} object" ]
        pairs.extend(f"{name} receives {self._describe_value(value)}" for name, value in zip(parameters[1:] if parameters and parameters[0] == "self" else parameters, args))
        return f"Method call {call_text}: " + "; ".join(pairs) + "."

    def _find_method(self, class_name: str, method_name: str) -> ast.FunctionDef | None:
        cls = self.classes.get(class_name)
        if cls is None:
            return None
        return next((item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == method_name), None)

    def _call_method(self, owner: _Instance, function: ast.FunctionDef, args: list[Any]) -> Any:
        parameters = [arg.arg for arg in function.args.args]
        if parameters and parameters[0] == "self":
            expected = parameters[1:]
        else:
            expected = parameters
        if len(args) != len(expected):
            raise RuntimeError(f"Method {function.name}() expects {len(expected)} argument(s), got {len(args)}.")
        frame = {"self": owner}
        frame.update(zip(expected, args))
        self.frames.append(frame)
        try:
            self._exec_block(function.body)
        except _ReturnSignal as signal:
            return signal.value
        finally:
            self.frames.pop()
        return None

    @staticmethod
    def _compare(op: ast.cmpop, left: Any, right: Any) -> bool:
        if isinstance(op, ast.Eq): return left == right
        if isinstance(op, ast.NotEq): return left != right
        if isinstance(op, ast.Is): return left is right
        if isinstance(op, ast.IsNot): return left is not right
        if isinstance(op, ast.Lt): return left < right
        if isinstance(op, ast.LtE): return left <= right
        if isinstance(op, ast.Gt): return left > right
        if isinstance(op, ast.GtE): return left >= right
        if isinstance(op, ast.In): return left in right
        if isinstance(op, ast.NotIn): return left not in right
        raise RuntimeError(f"Unsupported comparison: {type(op).__name__}")

    def _apply_binop(self, op: ast.operator, left: Any, right: Any) -> Any:
        if isinstance(op, ast.Mult):
            if isinstance(left, str) and isinstance(right, int) and len(left) * max(0, right) > self.max_string_characters:
                raise RuntimeError("String operation exceeds VisUAL's size limit.")
            if isinstance(right, str) and isinstance(left, int) and len(right) * max(0, left) > self.max_string_characters:
                raise RuntimeError("String operation exceeds VisUAL's size limit.")
        if isinstance(op, ast.Add): result = left + right
        elif isinstance(op, ast.Sub): result = left - right
        elif isinstance(op, ast.Mult): result = left * right
        elif isinstance(op, ast.Div): result = left / right
        elif isinstance(op, ast.FloorDiv): result = left // right
        elif isinstance(op, ast.Mod): result = left % right
        else: raise RuntimeError(f"Unsupported operator: {type(op).__name__}")
        if isinstance(result, str) and len(result) > self.max_string_characters:
            raise RuntimeError("String operation exceeds VisUAL's size limit.")
        if isinstance(result, int) and result.bit_length() > self.max_integer_bits:
            raise RuntimeError("Integer operation exceeds VisUAL's size limit.")
        return result

    def _append_output(self, text: str) -> None:
        self.output_characters += len(text) + 1
        if self.output_characters > self.max_output_characters:
            raise RuntimeError("Program output exceeded VisUAL's size limit.")
        self.output.append(text)

    @staticmethod
    def _display_value(value: Any) -> Any:
        if isinstance(value, _Instance):
            return f"<{value.class_name} #{value.identity}>"
        return value

    def _describe_value(self, value: Any) -> str:
        if value is _MISSING:
            return "not set"
        if isinstance(value, _Instance):
            return f"{value.class_name} #{value.identity}"
        return repr(value)

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, _Instance):
            return {"ref": value.identity, "class": value.class_name}
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (tuple, list)):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, ast.AST):
            return "<method>"
        return str(value)

    def _make_snapshot(self, node: ast.AST | None, event_type: str, explanation: str) -> dict:
        node_instances = [item for item in self.instances if item.class_name == "Node"]
        list_instances = [item for item in self.instances if item.class_name == "LinkedList"]
        # Display nodes reachable from any known list head, in linked order. Keep
        # each node once if the program has multiple list instances.
        ordered: list[_Instance] = []
        seen: set[int] = set()
        # The first LinkedList instance is the visualized structure. Other
        # instances remain visible in the variable/reference pane, but are not
        # merged into one misleading diagram.
        for linked_list in list_instances[:1]:
            current = linked_list.attrs.get("head")
            local_seen: set[int] = set()
            while isinstance(current, _Instance) and current.class_name == "Node":
                if current.identity in local_seen:
                    break  # prevent malformed/cyclic structures from hanging the visualizer
                local_seen.add(current.identity)
                if current.identity not in seen:
                    ordered.append(current)
                    seen.add(current.identity)
                current = current.attrs.get("next")
        if event_type == "object_creation":
            for instance in node_instances:
                if instance.identity not in seen:
                    ordered.append(instance)
                    seen.add(instance.identity)
        nodes = [{
            "id": item.identity,
            "data": self._serialize_value(item.attrs.get("data")),
            "next": item.attrs.get("next").identity if isinstance(item.attrs.get("next"), _Instance) and item.attrs.get("next").class_name == "Node" else None,
        } for item in ordered]
        head_ref = next((item.attrs.get("head").identity for item in list_instances if isinstance(item.attrs.get("head"), _Instance)), None)
        variables: dict[str, Any] = {}
        for frame in [self.globals, *self.frames]:
            for name, value in frame.items():
                if name.startswith("__") or isinstance(value, ast.AST):
                    continue
                variables[name] = self._serialize_value(value)
        variable_explanations = self._variable_explanations(variables, node, event_type)
        visualization = self._visualization_metadata(node, event_type)
        source = {
            "line": getattr(node, "lineno", 1) if node is not None else 1,
            "column": getattr(node, "col_offset", 0) + 1 if node is not None else 1,
            "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 1)) if node is not None else 1,
            "end_column": getattr(node, "end_col_offset", getattr(node, "col_offset", 0)) + 1 if node is not None else 1,
        }
        return {
            "step_index": len(self.snapshots), "source": source, "event_type": event_type,
            "nodes": nodes, "next_refs": {str(item["id"]): item["next"] for item in nodes},
            "head_ref": head_ref, "variables": variables, "explanation": explanation,
            "variable_explanations": variable_explanations,
            "visualization": visualization,
            "program_output": list(self.output), "status": self.status,
            "traversed_node_ref": self._traversed_node_ref,
        }

    def _visualization_metadata(self, node: ast.AST | None, event_type: str) -> dict:
        if event_type != "class_definition" or not isinstance(node, ast.ClassDef):
            return {"kind": "linked_list"}
        attributes = []
        for function in node.body:
            if not isinstance(function, ast.FunctionDef) or function.name != "__init__":
                continue
            for statement in function.body:
                if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                        if target.attr not in attributes:
                            attributes.append(target.attr)
        return {"kind": "class_blueprint", "class_name": node.name, "attributes": attributes}

    def _variable_explanations(self, variables: dict[str, Any], node: ast.AST | None, event_type: str) -> dict[str, dict[str, Any]]:
        explanations = {}
        relevant = self._relevant_variable_names(node, event_type)
        aliases: dict[tuple[str, int], list[str]] = {}
        for name, value in variables.items():
            if isinstance(value, dict) and isinstance(value.get("ref"), int):
                aliases.setdefault((value.get("class", "object"), value["ref"]), []).append(name)
        for name, value in variables.items():
            if relevant is not None and name not in relevant:
                continue
            if isinstance(value, dict) and value.get("class") == "Node":
                explanations[name] = {"value": value, "explanation": f"Refers to the node containing {self._node_data(value.get('ref'))}."}
                instance = next((item for item in self.instances if item.identity == value.get("ref")), None)
                if instance is not None:
                    selected_attributes = (
                        {item.split(".", 1)[1] for item in relevant if item.startswith(f"{name}.")}
                        if relevant is not None else set()
                    )
                    for attr, attr_value in instance.attrs.items():
                        key = f"{name}.{attr}"
                        if selected_attributes and attr not in selected_attributes:
                            continue
                        explanations[key] = {"value": self._serialize_value(attr_value), "explanation": self._attribute_explanation(attr, attr_value)}
            elif isinstance(value, dict) and value.get("class") == "LinkedList":
                peers = [peer for peer in aliases.get(("LinkedList", value["ref"]), []) if peer != name]
                if name == "self" and peers:
                    explanation = f"The method's current object; same object as {', '.join(peers)}."
                elif "self" in peers:
                    explanation = "The linked list object used to call the method."
                else:
                    explanation = "Refers to the linked list object used by the program."
                explanations[name] = {"value": value, "explanation": explanation}
            else:
                if self.frames and name in self.frames[-1] and name != "self":
                    explanation = "Argument or local value used by the current method."
                else:
                    explanation = "Current value used by the program."
                explanations[name] = {"value": value, "explanation": explanation}
        return explanations

    def _relevant_variable_names(self, node: ast.AST | None, event_type: str) -> set[str] | None:
        if node is None:
            return None
        names: set[str] = set()
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute):
                    target_text = ast.unparse(target)
                    names.add(target_text)
                    if isinstance(target.value, ast.Name):
                        names.add(target.value.id)
                elif isinstance(target, ast.Name):
                    names.add(target.id)
            names.update(item.id for item in ast.walk(node.value) if isinstance(item, ast.Name))
            return names
        if isinstance(node, ast.Call):
            names.update(item.id for item in ast.walk(node) if isinstance(item, ast.Name))
            if event_type == "method_call":
                names.update(self.frames[-1].keys() if self.frames else ())
            return names
        if isinstance(node, (ast.If, ast.While)):
            expression = node.test
            names.update(item.id for item in ast.walk(expression) if isinstance(item, ast.Name))
            return names
        if isinstance(node, ast.Expr):
            names.update(item.id for item in ast.walk(node.value) if isinstance(item, ast.Name))
            return names
        return None

    def _node_data(self, identity: int | None) -> Any:
        instance = next((item for item in self.instances if item.identity == identity), None)
        return self._serialize_value(instance.attrs.get("data")) if instance else "unknown"

    def _attribute_explanation(self, attr: str, value: Any) -> str:
        if attr == "data":
            return f"{self._describe_value(value)} — the value stored in the current node."
        if value is None:
            return "None — there is no next node referenced here."
        return f"Refers to the {value.class_name} object containing the next linked node." if isinstance(value, _Instance) else "Current attribute value."

    def _reference_explanation(self, owner: _Instance, attribute: str, value: Any, previous: Any) -> str:
        if attribute == "head":
            if value is None:
                return "The linked list's head reference is now None, so the list is empty."
            return (
                f"The linked list's head reference now points to the node containing {self._node_value(value)}. "
                "This node becomes the first node in the list."
            )
        if attribute == "next":
            target = "None" if value is None else f"the node containing {self._node_value(value)}"
            return f"The node containing {self._node_value(owner)} now points to {target} through its next reference."
        return (
            f"{owner.class_name} object's {attribute} changed from {self._describe_value(previous)} "
            f"to {self._describe_value(value)}."
        )

    def _node_value(self, value: Any) -> Any:
        if isinstance(value, _Instance):
            return self._describe_value(value.attrs.get("data"))
        return self._describe_value(value)

    def _node_reference_from_print(self, call: ast.Call) -> int | None:
        """Return the node ID printed by a supported traversal statement."""
        for argument in call.args:
            if isinstance(argument, ast.Attribute) and argument.attr == "data":
                value = self._eval(argument.value)
                if isinstance(value, _Instance) and value.class_name == "Node":
                    return value.identity
        return None

    def _record(self, node: ast.AST | None, event_type: str, explanation: str, force: bool = False) -> None:
        if len(self.snapshots) >= self.max_snapshots and not force:
            raise _StepLimit()
        snapshot = self._make_snapshot(node, event_type, explanation)
        if force:
            snapshot["step_index"] = len(self.snapshots)
        self.snapshots.append(freeze_snapshot(snapshot))
