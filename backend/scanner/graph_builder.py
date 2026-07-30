"""
Graph Builder
-------------
Turns the flat list of dependency edges into a networkx directed graph and
computes a few metrics that are directly useful for technical-debt scoring:

  - afferent coupling (Ca)  : how many OTHER classes depend on this class
  - efferent coupling (Ce)  : how many OTHER classes this class depends on
  - instability (I = Ce / (Ca + Ce)) : 0 = fully stable, 1 = fully unstable
  - cyclic_dependencies      : any dependency cycles found (a classic
                               architecture smell)
"""

import networkx as nx
from scanner.utils.logger import logger


def build_graph(classes, edges):
    graph = nx.DiGraph()

    for cls in classes:
        graph.add_node(
            cls.fully_qualified_name,
            name=cls.name,
            package=cls.package,
            class_type=cls.class_type,
        )

    for edge in edges:
        graph.add_edge(edge["from"], edge["to"], type=edge["type"])

    return graph


def compute_metrics(graph):
    metrics = {}

    for node in graph.nodes:
        ca = graph.in_degree(node)   # classes that depend on this one
        ce = graph.out_degree(node)  # classes this one depends on
        instability = ce / (ca + ce) if (ca + ce) > 0 else 0.0

        metrics[node] = {
            "afferent_coupling": ca,
            "efferent_coupling": ce,
            "instability": round(instability, 2),
        }

    return metrics


def find_cycles(graph):
    try:
        cycles = list(nx.simple_cycles(graph))
    except nx.NetworkXNoCycle:
        cycles = []
    return cycles


def build_and_analyze(classes, edges):
    """
    Convenience entry point used by the scanner service.
    Returns a dict ready to be merged into the project statistics.
    """
    graph = build_graph(classes, edges)
    metrics = compute_metrics(graph)
    cycles = find_cycles(graph)

    if cycles:
        logger.warning(f"Found {len(cycles)} circular dependency chain(s)")

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "coupling_metrics": metrics,
        "circular_dependencies": cycles,
    }
