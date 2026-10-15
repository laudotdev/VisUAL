"""Static validation for VisUAL's intentionally small Python subset.

This module only parses and inspects source. It never executes target code.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Diagnostic:
    message: str
    line: int = 1
    column: int = 1
    code: str = "visual.unsupported"

    def as_dict(self) -> dict:
        return {"message": self.message, "line": self.line, "column": self.column, "code": self.code}


@dataclass
class AnalysisResult:
    supported: bool
    node_class: str | None = None
    list_class: str | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)


_ALLOWED_STMTS = (
    ast.ClassDef, ast.FunctionDef, ast.Assign, ast.AnnAssign, ast.AugAssign,
    ast.Expr, ast.If, ast.While, ast.Return, ast.Break, ast.Continue, ast.Pass,
)
_ALLOWED_EXPRS = (
    ast.Name, ast.Constant, ast.Attribute, ast.Call, ast.Compare, ast.BinOp,
    ast.UnaryOp, ast.BoolOp, ast.IfExp,
    ast.Load, ast.Store, ast.keyword,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot,
    ast.In, ast.NotIn, ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd,
)

_FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "input", "breakpoint",
}


class _Validator(ast.NodeVisitor):
    def __init__(self, class_names: set[str] | None = None, method_names: set[str] | None = None) -> None:
        self.diagnostics: list[Diagnostic] = []
        self.class_names = class_names or set()
        self.method_names = method_names or set()

    def _add(self, node: ast.AST, message: str) -> None:
        self.diagnostics.append(Diagnostic(
            message=message,
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 0) + 1,
        ))

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            self._add(node, "Imports are not supported by VisUAL's controlled interpreter.")
            return
        if isinstance(node, (ast.For, ast.AsyncFor, ast.AsyncFunctionDef, ast.With, ast.AsyncWith,
                              ast.Try, ast.Raise, ast.Lambda, ast.Yield, ast.YieldFrom,
                              ast.Global, ast.Nonlocal, ast.Delete, ast.Set, ast.DictComp,
                              ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.Await, ast.Match)):
            self._add(node, f"'{type(node).__name__}' is not supported by VisUAL yet.")
            return
        if isinstance(node, ast.stmt) and not isinstance(node, _ALLOWED_STMTS):
            self._add(node, f"Statement '{type(node).__name__}' is not supported by VisUAL yet.")
            return
        if isinstance(node, ast.expr) and not isinstance(node, _ALLOWED_EXPRS):
            self._add(node, f"Expression '{type(node).__name__}' is not supported by VisUAL yet.")
            return
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            self._add(node, f"'{node.id}()' is not supported by VisUAL.")
            return
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id.startswith("__"):
                self._add(node, "Dunder and reflective calls are not supported by VisUAL.")
                return
        super().generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, (str, int, bool, type(None))):
            self._add(node, "Only None, booleans, integers, and strings are supported as literals.")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in self.class_names | {"print", "int", "str", "bool"}:
                self._add(node, f"Call to '{name}()' is not supported by VisUAL.")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr not in self.method_names:
                self._add(node, f"Method call '{node.func.attr}()' is not defined in the supported classes.")
        else:
            self._add(node, "Dynamic and indirect function calls are not supported by VisUAL.")
        if node.keywords:
            self._add(node, "Keyword arguments are not supported by VisUAL yet.")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.bases or node.decorator_list or node.keywords:
            self._add(node, "Inheritance, class decorators, and class keywords are not supported by VisUAL.")
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.Assign, ast.AnnAssign, ast.Pass, ast.Expr)):
                self._add(item, "Only methods and simple class-body declarations are supported inside classes.")
                continue
            self.visit(item)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.decorator_list or node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
            self._add(node, "Decorators, *args, **kwargs, and keyword-only parameters are not supported.")
        if node.args.defaults and len(node.args.defaults) > 0:
            self._add(node, "Default parameter values are not supported by VisUAL yet.")
        for arg in node.args.args:
            if arg.annotation:
                self._add(arg, "Type annotations on parameters are not supported by VisUAL yet.")
        for item in node.body:
            self.visit(item)


def analyze_source(source: str) -> AnalysisResult:
    """Parse, detect, and validate a conventional Node + LinkedList program."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return AnalysisResult(False, diagnostics=[Diagnostic(
            f"Python syntax error: {exc.msg}", exc.lineno or 1, exc.offset or 1, "visual.syntax"
        )])

    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    if "Node" not in classes or "LinkedList" not in classes:
        return AnalysisResult(False, diagnostics=[Diagnostic(
            "VisUAL expects conventional top-level classes named Node and LinkedList.", 1, 1,
            "visual.pattern"
        )])

    node_class = classes["Node"]
    list_class = classes["LinkedList"]
    node_fields = set()
    list_fields = set()
    for cls, fields in ((node_class, node_fields), (list_class, list_fields)):
        for method in (item for item in cls.body if isinstance(item, ast.FunctionDef)):
            for sub in ast.walk(method):
                if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                    fields.add(sub.attr)
    if not {"data", "next"}.issubset(node_fields):
        return AnalysisResult(False, diagnostics=[Diagnostic(
            "Node must define conventional self.data and self.next fields.", node_class.lineno, 1,
            "visual.pattern"
        )])
    if "head" not in list_fields:
        return AnalysisResult(False, diagnostics=[Diagnostic(
            "LinkedList must define a conventional self.head field.", list_class.lineno, 1,
            "visual.pattern"
        )])

    method_names = {
        item.name
        for cls in classes.values()
        for item in cls.body
        if isinstance(item, ast.FunctionDef)
    }
    validator = _Validator(set(classes), method_names)
    validator.visit(tree)

    # Recursion is intentionally outside the initial execution contract.
    method_nodes = {
        item.name: item
        for cls in classes.values()
        for item in cls.body
        if isinstance(item, ast.FunctionDef)
    }
    call_graph: dict[str, set[str]] = {name: set() for name in method_nodes}
    for method_name, method_node in method_nodes.items():
        for sub in ast.walk(method_node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in method_nodes:
                call_graph[method_name].add(sub.func.attr)
    def reaches_self(start: str, current: str, visited: set[str]) -> bool:
        for target in call_graph.get(current, set()):
            if target == start:
                return True
            if target not in visited and reaches_self(start, target, visited | {target}):
                return True
        return False
    recursive = [name for name in call_graph if reaches_self(name, name, {name})]
    if recursive:
        method_node = method_nodes[recursive[0]]
        validator.diagnostics.append(Diagnostic(
            "Recursive method calls are not supported by VisUAL yet.",
            method_node.lineno, 1, "visual.recursion"
        ))
    if validator.diagnostics:
        # Avoid flooding the UI with repeated copies of the same issue.
        unique = []
        seen = set()
        for diagnostic in validator.diagnostics:
            key = (diagnostic.message, diagnostic.line, diagnostic.column)
            if key not in seen:
                unique.append(diagnostic)
                seen.add(key)
        return AnalysisResult(False, "Node", "LinkedList", unique[:30])

    # Only accept source that actually creates/uses a LinkedList instance.
    uses_list = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "LinkedList"
        for node in ast.walk(tree)
    )
    if not uses_list:
        return AnalysisResult(False, "Node", "LinkedList", [Diagnostic(
            "The program defines linked-list classes but does not create a LinkedList instance.",
            list_class.lineno, 1, "visual.no_instance"
        )])

    return AnalysisResult(True, "Node", "LinkedList", [])
