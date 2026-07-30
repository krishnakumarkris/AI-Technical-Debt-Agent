"""
Java AST Parser
---------------
Parses a single .java source file into a ClassModel (or list of ClassModel,
since one file can contain multiple top-level types) using `javalang`.

Extracts:
  - package declaration
  - imports
  - class / interface / enum name + kind
  - modifiers & annotations
  - extends / implements
  - fields (name, type, modifiers, line)
  - methods (name, return type, parameters, modifiers, annotations, line,
    approximate line_count)
  - constructors (modeled as methods with is_constructor=True)
"""

import hashlib

import javalang

from scanner.models.project_model import (
    ClassModel,
    FieldModel,
    MethodModel,
    ParameterModel,
)
from scanner.utils.logger import logger


def _type_name(type_node):
    """
    javalang represents types as BasicType / ReferenceType / None (void).
    Convert any of these into a readable string, including array dimensions
    and generic arguments where present.
    """
    if type_node is None:
        return "void"

    name = getattr(type_node, "name", str(type_node))

    # Generic arguments, e.g. List<String>
    arguments = getattr(type_node, "arguments", None)
    if arguments:
        arg_names = []
        for arg in arguments:
            inner = getattr(arg, "type", None)
            arg_names.append(_type_name(inner) if inner else "?")
        name = f"{name}<{', '.join(arg_names)}>"

    dimensions = getattr(type_node, "dimensions", None)
    if dimensions:
        name += "[]" * len(dimensions)

    return name


def _annotation_names(annotations):
    return [a.name for a in (annotations or [])]


def _extends_name(extends_node):
    """
    ClassDeclaration.extends -> a single ReferenceType (or None).
    InterfaceDeclaration.extends -> a list of ReferenceType (or None).
    Normalize both cases to a single comma-joined string.
    """
    if extends_node is None:
        return ""
    if isinstance(extends_node, list):
        return ", ".join(_type_name(e) for e in extends_node)
    return _type_name(extends_node)


def _implements_names(implements_node):
    if not implements_node:
        return []
    return [_type_name(i) for i in implements_node]


def _class_kind(node):
    kind = type(node).__name__
    return {
        "ClassDeclaration": "class",
        "InterfaceDeclaration": "interface",
        "EnumDeclaration": "enum",
        "RecordDeclaration": "record",
    }.get(kind, kind)


def _parse_field(member):
    """A single FieldDeclaration can declare multiple variables (declarators)."""
    fields = []
    datatype = _type_name(member.type)
    line = member.position.line if member.position else 0
    for declarator in member.declarators:
        fields.append(
            FieldModel(
                name=declarator.name,
                datatype=datatype,
                modifiers=sorted(member.modifiers),
                line_number=line,
            )
        )
    return fields


def _parse_parameters(params):
    result = []
    for p in params:
        result.append(ParameterModel(name=p.name, datatype=_type_name(p.type)))
    return result


def _estimate_line_count(member, all_members, source_lines_total):
    """
    javalang's AST does not give an explicit "end line" for a method, so we
    approximate method length as the distance to the next sibling member's
    start line (or end-of-class for the last member). This is good enough to
    flag "long method" candidates without needing a second, position-aware
    parser pass.
    """
    if member.position is None:
        return 0

    start = member.position.line
    later_starts = [
        m.position.line
        for m in all_members
        if m.position and m.position.line > start
    ]
    end = min(later_starts) if later_starts else source_lines_total + 1
    return max(end - start, 1)


def _hash_body(source_lines, start_line, line_count):
    """
    Build a normalized hash of a method's body text so that two methods with
    identical logic (ignoring whitespace, blank lines and comments) can be
    flagged as exact-clone duplicates later, without needing a full clone-
    detection library.

    Returns (hash_string, non_blank_line_count). An empty hash means there
    was nothing meaningful to hash (e.g. an abstract method with no body).
    """
    if start_line <= 0 or line_count <= 0:
        return "", 0

    # Skip the first line (method/constructor signature) so that two methods
    # with identical bodies but different names/parameter names still hash
    # the same - it's the BODY that's duplicated, not the signature.
    snippet = source_lines[start_line: start_line - 1 + line_count]

    normalized = []
    for line in snippet:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        normalized.append(stripped)

    if not normalized:
        return "", 0

    joined = "\n".join(normalized)
    digest = hashlib.md5(joined.encode("utf-8")).hexdigest()
    return digest, len(normalized)


def parse_java_file(file_path):
    """
    Parse one .java file.
    Returns (list_of_ClassModel, error_message_or_None).
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except OSError as e:
        return [], f"Could not read file: {e}"

    total_lines = source.count("\n") + 1
    source_lines = source.splitlines()

    try:
        tree = javalang.parse.parse(source)
    except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return [], f"Syntax error: {e}"
    except Exception as e:  # javalang can raise plain Exception on malformed input
        logger.warning(f"Failed to parse {file_path}: {e}")
        return [], f"Parse failure: {e}"

    package_name = tree.package.name if tree.package else ""
    imports = [imp.path for imp in tree.imports]

    classes = []

    for type_node in tree.types:
        class_type = _class_kind(type_node)

        class_model = ClassModel(
            name=type_node.name,
            package=package_name,
            file_path=str(file_path),
            class_type=class_type,
            modifiers=sorted(getattr(type_node, "modifiers", set()) or []),
            imports=imports,
            extends=_extends_name(getattr(type_node, "extends", None)),
            implements=_implements_names(getattr(type_node, "implements", None)),
            annotations=_annotation_names(getattr(type_node, "annotations", None)),
        )

        body = getattr(type_node, "body", None) or []

        # Enums store their body members under a different attribute set in
        # javalang (constants + body); guard for that.
        members_with_position = [m for m in body if getattr(m, "position", None)]

        for member in body:
            if isinstance(member, javalang.tree.FieldDeclaration):
                class_model.fields.extend(_parse_field(member))

            elif isinstance(member, javalang.tree.ConstructorDeclaration):
                line = member.position.line if member.position else 0
                line_count = _estimate_line_count(
                    member, members_with_position, total_lines
                )
                body_hash, non_blank = _hash_body(source_lines, line, line_count)
                class_model.methods.append(
                    MethodModel(
                        name=member.name,
                        return_type="",
                        parameters=_parse_parameters(member.parameters),
                        modifiers=sorted(member.modifiers),
                        annotations=_annotation_names(member.annotations),
                        line_number=line,
                        line_count=line_count,
                        is_constructor=True,
                        non_blank_lines=non_blank,
                        body_hash=body_hash,
                    )
                )

            elif isinstance(member, javalang.tree.MethodDeclaration):
                line = member.position.line if member.position else 0
                line_count = _estimate_line_count(
                    member, members_with_position, total_lines
                )
                body_hash, non_blank = _hash_body(source_lines, line, line_count)
                class_model.methods.append(
                    MethodModel(
                        name=member.name,
                        return_type=_type_name(member.return_type),
                        parameters=_parse_parameters(member.parameters),
                        modifiers=sorted(member.modifiers),
                        annotations=_annotation_names(member.annotations),
                        line_number=line,
                        line_count=line_count,
                        is_constructor=False,
                        non_blank_lines=non_blank,
                        body_hash=body_hash,
                    )
                )

        class_model.line_count = total_lines
        classes.append(class_model)

    return classes, None
