"""
Dependency Parser
-----------------
Given all the ClassModel objects discovered by the AST parser, this module
figures out which classes depend on which OTHER classes *inside the same
project* (external/library types are ignored, since they aren't something
the technical-debt agent can refactor).

A dependency edge A -> B is recorded when class A:
  - extends B
  - implements B
  - has a field of type B
  - has a method parameter or return type of type B

Matching is done by simple class name (not fully-qualified), which is good
enough for typical single-package-per-name projects and avoids having to
fully resolve wildcard/star imports.
"""

from scanner.utils.logger import logger


def _strip_generics(type_name: str) -> str:
    """'List<User>' -> 'List', 'User[]' -> 'User'"""
    return type_name.split("<")[0].replace("[]", "").strip()


def build_dependency_edges(classes):
    """
    classes: list[ClassModel]
    Returns: list[dict] of {"from": fqn, "to": fqn, "type": relation}
    """
    # Map simple class name -> fully qualified name, for resolution
    name_to_fqn = {c.name: c.fully_qualified_name for c in classes}

    edges = []
    seen = set()

    def add_edge(source_fqn, target_simple_name, relation):
        target_simple_name = _strip_generics(target_simple_name)
        if not target_simple_name or target_simple_name not in name_to_fqn:
            return  # external / library type, or unknown -> skip
        target_fqn = name_to_fqn[target_simple_name]
        if target_fqn == source_fqn:
            return  # ignore self references
        key = (source_fqn, target_fqn, relation)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": source_fqn, "to": target_fqn, "type": relation})

    for cls in classes:
        source = cls.fully_qualified_name

        if cls.extends:
            for parent in cls.extends.split(","):
                add_edge(source, parent.strip(), "extends")

        for iface in cls.implements:
            add_edge(source, iface, "implements")

        for f in cls.fields:
            add_edge(source, f.datatype, "field")

        for m in cls.methods:
            if m.return_type:
                add_edge(source, m.return_type, "return_type")
            for p in m.parameters:
                add_edge(source, p.datatype, "parameter")

    logger.info(f"Resolved {len(edges)} internal dependency edges")
    return edges
