from __future__ import annotations

import copy
from queue import PriorityQueue
import networkx as nx
from networkx import DiGraph
from shapely.geometry import Point, LineString
import warnings

warnings.filterwarnings(
    "ignore",
    message="the convert_dtype parameter is deprecated and will be removed in a future version"
)


def get_incident_arcs(v: int, graph: DiGraph) -> tuple[list[tuple[int, int, dict]], list[tuple[int, int, dict]]]:
    """Get the incoming and outgoing arcs of a node, excluding self-loops."""
    in_edges = [(u, w, data) for u, w, data in graph.in_edges(v, data=True) if u != v]
    out_edges = [(u, w, data) for u, w, data in graph.out_edges(v, data=True) if w != v]
    return in_edges, out_edges


def isolate_node(graph: DiGraph, in_edges: list[tuple[int, int, dict]], out_edges: list[tuple[int, int, dict]]) -> None:
    """Remove all incoming and outgoing edges of a node."""
    graph.remove_edges_from(in_edges)
    graph.remove_edges_from(out_edges)


def get_lengths_and_geometries_incident_arcs(
        in_arcs: list[tuple[int, int, dict]], out_arcs: list[tuple[int, int, dict]]
) -> tuple[dict[int, tuple[float, object]], dict[int, tuple[float, object]]]:
    """Retrieve the lengths and geometries of incoming and outgoing arcs."""
    in_arcs_lengths_geometries = {u: (data["length"], data["geometry"]) for u, _, data in in_arcs}
    out_arcs_lengths_geometries = {w: (data["length"], data["geometry"]) for _, w, data in out_arcs}
    return in_arcs_lengths_geometries, out_arcs_lengths_geometries


def get_shortcuts(
        u: int,
        graph: DiGraph,
        in_arcs_lengths_geom: dict[int, tuple[float, object]],
        out_arcs_lengths_geom: dict[int, tuple[float, object]],
) -> list[tuple[int, int, dict]]:
    """Calculate shortcuts to reduce graph complexity."""
    pw = {w: in_arcs_lengths_geom[u][0] + out_arcs_lengths_geom[w][0] for w in out_arcs_lengths_geom}
    p_max = max(pw.values())

    distances, _ = nx.single_source_dijkstra(graph, source=u, cutoff=p_max, weight="length")

    w_targets = [w for w in out_arcs_lengths_geom if w not in distances or distances[w] > pw[w]]

    shortcuts = []
    for w in w_targets:
        geom_u_v = in_arcs_lengths_geom[u][1]
        geom_v_w = out_arcs_lengths_geom[w][1]
        combined_geometry = LineString(list(geom_u_v.coords) + list(geom_v_w.coords))

        shortcut = (
            u,
            w,
            {
                "length": pw[w],
                "u_original": u,
                "v_original": w,
                "origin": u,
                "destination": w,
                "type_of_arc": "shortcut",
                "coordinates_origin": Point(graph.nodes[u]["x"], graph.nodes[u]["y"]),
                "coordinates_destination": Point(graph.nodes[w]["x"], graph.nodes[w]["y"]),
                "geometry": combined_geometry,
            },
        )
        shortcuts.append(shortcut)

    return shortcuts


def restore_graph(graph: DiGraph, all_shortcuts: list[tuple[int, int, dict]], in_arcs: list[tuple[int, int, dict]],
                  out_arcs: list[tuple[int, int, dict]]):
    """Restore the graph after contraction by removing shortcuts and adding original arcs."""
    graph.remove_edges_from(all_shortcuts)
    graph.add_edges_from(in_arcs)
    graph.add_edges_from(out_arcs)


def get_edge_difference(v: int, graph: DiGraph) -> int:
    """Calculate the difference in number of edges after potential node contraction."""
    in_arcs, out_arcs = get_incident_arcs(v, graph)
    num_incident_edges = len(in_arcs) + len(out_arcs)
    if not in_arcs or not out_arcs:
        return 0
    in_arcs_lengths_geom, out_arcs_lengths_geom = get_lengths_and_geometries_incident_arcs(in_arcs, out_arcs)
    isolate_node(graph, in_arcs, out_arcs)
    all_shortcuts = []
    for u in in_arcs_lengths_geom:
        shortcuts = get_shortcuts(u, graph, in_arcs_lengths_geom, out_arcs_lengths_geom)
        graph.add_edges_from(shortcuts)
        all_shortcuts.extend(shortcuts)
    restore_graph(graph, all_shortcuts, in_arcs, out_arcs)
    return len(all_shortcuts) - num_incident_edges


def get_node_ordering(graph: DiGraph) -> PriorityQueue:
    """Create a priority queue of nodes based on their edge difference for graph contraction."""
    node_ordering = PriorityQueue()
    for v in graph.nodes:
        edge_difference = get_edge_difference(v, graph)
        node_ordering.put((edge_difference, v))
    return node_ordering


def _contract_node(v: int, graph: DiGraph, graph_contracted: DiGraph) -> None:
    """Contract a node in the graph, obtaining shortcuts and adding them to the graphs."""
    in_arcs, out_arcs = get_incident_arcs(v, graph_contracted)
    if not in_arcs or not out_arcs:
        return
    in_arcs_length_geom, out_arcs_lengths_geom = get_lengths_and_geometries_incident_arcs(in_arcs, out_arcs)
    graph_contracted.remove_node(v)
    for u in in_arcs_length_geom:
        shortcuts = get_shortcuts(u, graph_contracted, in_arcs_length_geom, out_arcs_lengths_geom)
        graph.add_edges_from(shortcuts)
        graph_contracted.add_edges_from(shortcuts)


def add_shortcuts_to_graph(graph: DiGraph) -> None:
    """Add shortcuts to graph using contraction hierarchy preprocessing."""
    node_ordering_pq = get_node_ordering(graph)
    edges_before = len(graph.edges())
    print(f"Number of arcs before augmenting the graph: {edges_before}")
    graph_contracted = copy.deepcopy(graph)
    while not node_ordering_pq.empty():
        edge_difference, v = node_ordering_pq.get()
        new_edge_diff = get_edge_difference(v, graph_contracted)
        if new_edge_diff > edge_difference:
            node_ordering_pq.put((new_edge_diff, v))
            continue
        _contract_node(v, graph, graph_contracted)
    edges_after = len(graph.edges())
    print(f"Shortcuts added: {edges_after - edges_before}")
