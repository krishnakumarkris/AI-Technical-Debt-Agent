"""
Method-level static analysis helpers used by debt detection rules.

Walks a javalang method/constructor body and extracts metrics such as
cyclomatic complexity, nesting depth, empty catch blocks, magic numbers,
unused locals, and security heuristics.
"""

import re

import javalang

COMMON_MAGIC_NUMBERS = {0, 1, -1, 2, 10, 100}

CREDENTIAL_NAME_PATTERN = re.compile(
    r"(password|passwd|secret|api[_-]?key|token|credential)",
    re.IGNORECASE,
)

RESOURCE_TYPE_KEYWORDS = (
    "Stream",
    "Reader",
    "Writer",
    "Connection",
    "Statement",
    "ResultSet",
    "Socket",
    "Channel",
)

CONTROL_NODES = (
    javalang.tree.IfStatement,
    javalang.tree.ForStatement,
    javalang.tree.WhileStatement,
    javalang.tree.DoStatement,
    javalang.tree.SwitchStatement,
    javalang.tree.TryStatement,
    javalang.tree.CatchClause,
    javalang.tree.SynchronizedStatement,
)

LOOP_NODES = (
    javalang.tree.ForStatement,
    javalang.tree.WhileStatement,
    javalang.tree.DoStatement,
)


def _line(node, fallback=0):
    if getattr(node, "position", None):
        return node.position.line
    return fallback


def _type_name(type_node):
    if type_node is None:
        return ""
    if isinstance(type_node, str):
        return type_node
    name = getattr(type_node, "name", str(type_node))
    dimensions = getattr(type_node, "dimensions", None)
    if dimensions:
        name += "[]" * len(dimensions)
    return name


def _is_resource_type(type_name):
    return any(keyword in type_name for keyword in RESOURCE_TYPE_KEYWORDS)


def _has_javadoc(source_lines, method_line):
    if method_line <= 1:
        return False
    for idx in range(method_line - 2, max(method_line - 8, -1), -1):
        stripped = source_lines[idx].strip()
        if not stripped:
            continue
        if stripped.startswith("/**"):
            return True
        if stripped.startswith("*") or stripped.endswith("*/"):
            continue
        return False
    return False


def _walk_nodes(root):
    """Yield (path, node) pairs from a javalang Node or list of nodes."""
    if root is None:
        return
    if isinstance(root, list):
        for item in root:
            yield from _walk_nodes(item)
        return
    if not isinstance(root, javalang.ast.Node):
        return
    yield (), root
    for path, node in root:
        yield path, node


def _is_inside_loop(path_nodes):
    return any(isinstance(n, LOOP_NODES) for n in path_nodes)


def analyze_method_body(member, source_lines, class_name, parameters=None):
    """
    Returns a dict of metrics extracted from one method/constructor body.
    """
    parameters = parameters or []
    param_types = {p.name: p.datatype for p in parameters}

    method_line = _line(member)
    metrics = {
        "cyclomatic_complexity": 1,
        "max_nesting_depth": 0,
        "empty_catch_lines": [],
        "magic_numbers": [],
        "unused_local_vars": [],
        "string_concat_in_loop_line": 0,
        "unclosed_resource_lines": [],
        "catches_generic_exception_line": 0,
        "method_calls": [],
        "external_type_accesses": {},
        "parameter_type_accesses": {},
        "has_javadoc": _has_javadoc(source_lines, method_line),
        "hardcoded_credential_lines": [],
    }

    body = getattr(member, "body", None)
    if not body:
        return metrics

    local_vars = {}
    local_var_lines = {}

    for path, node in _walk_nodes(body):
        path_nodes = [item for item in path if isinstance(item, javalang.ast.Node)]

        if isinstance(node, CONTROL_NODES):
            depth = sum(1 for n in path_nodes if isinstance(n, CONTROL_NODES)) + 1
            metrics["max_nesting_depth"] = max(metrics["max_nesting_depth"], depth)

        if isinstance(
            node,
            (
                javalang.tree.IfStatement,
                javalang.tree.ForStatement,
                javalang.tree.WhileStatement,
                javalang.tree.DoStatement,
                javalang.tree.CatchClause,
            ),
        ):
            metrics["cyclomatic_complexity"] += 1

        if isinstance(node, javalang.tree.SwitchStatementCase):
            if node.case:
                metrics["cyclomatic_complexity"] += 1

        if isinstance(node, javalang.tree.BinaryOperation):
            if node.operator in ("&&", "||"):
                metrics["cyclomatic_complexity"] += 1
            if node.operator == "+" and _is_inside_loop(path_nodes):
                line = _line(node)
                if not line:
                    for ancestor in reversed(path_nodes):
                        line = _line(ancestor)
                        if line:
                            break
                metrics["string_concat_in_loop_line"] = (
                    metrics["string_concat_in_loop_line"] or line or method_line
                )

        if isinstance(node, javalang.tree.TernaryExpression):
            metrics["cyclomatic_complexity"] += 1

        if isinstance(node, javalang.tree.CatchClause):
            types = node.parameter.types if node.parameter else []
            caught = _type_name(types[0]) if types else ""
            if caught in ("Exception", "Throwable"):
                metrics["catches_generic_exception_line"] = (
                    metrics["catches_generic_exception_line"]
                    or _line(node, method_line)
                )
            block = node.block
            is_empty = False
            if block is None:
                is_empty = True
            elif isinstance(block, list):
                is_empty = len(block) == 0
            elif hasattr(block, "statements"):
                is_empty = not block.statements
            if is_empty:
                metrics["empty_catch_lines"].append(_line(node, method_line))

        if isinstance(node, javalang.tree.LocalVariableDeclaration):
            type_name = _type_name(node.type)
            for declarator in node.declarators:
                local_vars[declarator.name] = False
                local_var_lines[declarator.name] = _line(node, method_line)

                if _is_resource_type(type_name):
                    in_try_with_resources = any(
                        isinstance(n, javalang.tree.TryStatement)
                        and getattr(n, "resources", None)
                        for n in path_nodes
                    )
                    if not in_try_with_resources:
                        metrics["unclosed_resource_lines"].append(
                            _line(node, method_line)
                        )

                initializer = declarator.initializer
                if initializer and isinstance(initializer, javalang.tree.Literal):
                    if CREDENTIAL_NAME_PATTERN.search(declarator.name):
                        if initializer.value not in (None, "null", '""', "''"):
                            metrics["hardcoded_credential_lines"].append(
                                {
                                    "line": _line(node, method_line),
                                    "name": declarator.name,
                                }
                            )

        if isinstance(node, javalang.tree.MemberReference):
            if node.member in local_vars:
                # Pure write (assignment LHS) still counts as a "use" for now only
                # when read elsewhere; assignment handling marks used below.
                pass

        if isinstance(node, javalang.tree.MethodInvocation):
            metrics["method_calls"].append(node.member)
            qualifier = node.qualifier
            if qualifier and qualifier not in ("this", "super"):
                if qualifier in param_types:
                    target_type = param_types[qualifier]
                    metrics["parameter_type_accesses"][target_type] = (
                        metrics["parameter_type_accesses"].get(target_type, 0) + 1
                    )
                elif qualifier in local_vars:
                    metrics["external_type_accesses"][qualifier] = (
                        metrics["external_type_accesses"].get(qualifier, 0) + 1
                    )
                    local_vars[qualifier] = True
            # Arguments referencing locals count as reads.
            for arg in node.arguments or []:
                if isinstance(arg, javalang.tree.MemberReference) and arg.member in local_vars:
                    local_vars[arg.member] = True

        if isinstance(node, javalang.tree.Literal):
            if node.value is None:
                continue
            raw = str(node.value)
            if raw.startswith('"') or raw.startswith("'"):
                continue
            try:
                if "." in raw:
                    numeric = float(raw)
                else:
                    numeric = int(raw)
            except ValueError:
                continue
            if numeric not in COMMON_MAGIC_NUMBERS:
                metrics["magic_numbers"].append(
                    {"value": numeric, "line": _line(node, method_line)}
                )

        if isinstance(node, javalang.tree.Assignment):
            # Assignment alone does not count as a read of the local.
            if isinstance(node.value, javalang.tree.MemberReference):
                right = node.value.member
                if right in local_vars:
                    local_vars[right] = True
            if isinstance(node.value, javalang.tree.Literal):
                left = getattr(node.expressionl, "member", "")
                if CREDENTIAL_NAME_PATTERN.search(str(left)):
                    if node.value.value not in (None, "null", '""', "''"):
                        metrics["hardcoded_credential_lines"].append(
                            {"line": _line(node, method_line), "name": str(left)}
                        )

        if isinstance(node, javalang.tree.ReturnStatement):
            expr = node.expression
            if isinstance(expr, javalang.tree.MemberReference) and expr.member in local_vars:
                local_vars[expr.member] = True
            if isinstance(expr, javalang.tree.BinaryOperation):
                for side in (expr.operandl, expr.operandr):
                    if isinstance(side, javalang.tree.MemberReference) and side.member in local_vars:
                        local_vars[side.member] = True

        if isinstance(node, javalang.tree.BinaryOperation):
            for side in (node.operandl, node.operandr):
                if isinstance(side, javalang.tree.MemberReference) and side.member in local_vars:
                    local_vars[side.member] = True

        if isinstance(node, javalang.tree.MemberReference):
            # Any non-assignment reference is treated as a read.
            parent_is_assign_target = False
            if path_nodes:
                parent = path_nodes[-1]
                if isinstance(parent, javalang.tree.Assignment) and parent.expressionl is node:
                    parent_is_assign_target = True
            if node.member in local_vars and not parent_is_assign_target:
                local_vars[node.member] = True

    for name, used in local_vars.items():
        if not used:
            metrics["unused_local_vars"].append(
                {"name": name, "line": local_var_lines.get(name, 0)}
            )

    return metrics
