from __future__ import annotations

import copy
import pandas as pd
from queue import PriorityQueue
from typing import List, Tuple, Dict
import networkx as nx
from networkx import DiGraph
from shapely.geometry import Point, LineString
from instance_module.graph import reduce_graph
from instance_module.paths import get_node_based_shortest_paths
from input_data import InstanceParameters

import warnings

warnings.filterwarnings("ignore",
                        message="the convert_dtype parameter is deprecated and will be removed in a future version")


def get_incident_arcs(v: int, G: nx.DiGraph) -> Tuple[List[Tuple[int, int, dict]], List[Tuple[int, int, dict]]]:
    """Return incoming and outgoing arcs of node v, excluding self-loops."""

    # Get incoming and outgoing edges with data
    in_edges = [(u, w, data) for u, w, data in G.in_edges(v, data=True) if u != v]
    out_edges = [(u, w, data) for u, w, data in G.out_edges(v, data=True) if w != v]

    return in_edges, out_edges


def isolate_node(G: DiGraph, in_edges: List[Tuple[int, int, dict]], out_edges: List[Tuple[int, int, dict]]) -> None:
    """Remove all incoming and outgoing edges of a node."""
    G.remove_edges_from(in_edges)
    G.remove_edges_from(out_edges)


def get_lengths_incident_arcs(in_arcs: List[Tuple[int, int, dict]], out_arcs: List[Tuple[int, int, dict]]) -> (
        Tuple)[Dict[int, float], Dict[int, float]]:
    """Retrieve the lengths of incoming and outgoing arcs."""
    in_arcs_lengths = {u: data["length"] for u, _, data in in_arcs}
    out_arcs_lengths = {w: data["length"] for _, w, data in out_arcs}
    return in_arcs_lengths, out_arcs_lengths


def get_shortcuts(u: int, G: DiGraph, in_arcs_lengths: Dict[int, float], out_arcs_lengths: Dict[int, float]) -> (
        List)[Tuple[int, int, dict]]:
    """Calculate shortcuts to reduce graph complexity."""
    pw = {w: in_arcs_lengths[u] + out_arcs_lengths[w] for w in out_arcs_lengths}  # path weight through u
    p_max = max(pw.values())
    distances, _ = nx.single_source_dijkstra(G, source=u, cutoff=p_max, weight="length")
    w_targets = [w for w in out_arcs_lengths if w not in distances or distances[w] > pw[w]]
    shortcuts = [(u, w, {"length": pw[w], "origin": u, "destination": w, "type_of_arc": "shortcut",
                         "coordinates_origin": Point(G.nodes[u]["x"], G.nodes[u]["y"]),
                         "coordinates_destination": Point(G.nodes[w]["x"], G.nodes[w]["y"]),
                         "geometry": LineString([Point(G.nodes[u]["x"], G.nodes[u]["y"]),
                                                 Point(G.nodes[w]["x"], G.nodes[w]["y"])])})
                 for w in w_targets]
    return shortcuts


def restore_graph(G: DiGraph, all_shortcuts: List[Tuple[int, int, dict]], in_arcs: List[Tuple[int, int, dict]],
                  out_arcs: List[Tuple[int, int, dict]]):
    """Restore the graph after contraction by removing shortcuts and adding original arcs."""
    G.remove_edges_from(all_shortcuts)
    G.add_edges_from(in_arcs)
    G.add_edges_from(out_arcs)


def get_edge_difference(v: int, graph: DiGraph) -> int:
    """Calculate the difference in number of edges after potential node contraction."""
    in_arcs, out_arcs = get_incident_arcs(v, graph)
    num_incident_edges = len(in_arcs) + len(out_arcs)
    if not in_arcs or not out_arcs:
        return 0
    in_arcs_lengths, out_arcs_lengths = get_lengths_incident_arcs(in_arcs, out_arcs)
    isolate_node(graph, in_arcs, out_arcs)
    all_shortcuts = []
    for u in in_arcs_lengths:
        shortcuts = get_shortcuts(u, graph, in_arcs_lengths, out_arcs_lengths)
        graph.add_edges_from(shortcuts)
        all_shortcuts.extend(shortcuts)
    restore_graph(graph, all_shortcuts, in_arcs, out_arcs)
    edge_difference = len(all_shortcuts) - num_incident_edges
    return edge_difference


def get_node_ordering(graph: DiGraph) -> PriorityQueue:
    """Create a priority queue of nodes based on their edge difference for graph contraction."""
    node_ordering = PriorityQueue()
    for v in graph.nodes:
        edge_difference = get_edge_difference(v, graph)
        node_ordering.put((edge_difference, v))
    return node_ordering


def _contract_node(v: int, graph: DiGraph, GContracted: DiGraph) -> None:
    """
    contract node v on GContracted, obtain the relative shortcuts and add them both to GContracted and graph

    """
    inArcs, outArcs = get_incident_arcs(v, GContracted)
    if not inArcs or not outArcs:
        return
    inArcsLengths, outArcsLengths = get_lengths_incident_arcs(inArcs, outArcs)
    GContracted.remove_node(v)
    for u in inArcsLengths:
        shortcuts = get_shortcuts(u, GContracted, inArcsLengths, outArcsLengths)
        graph.add_edges_from(shortcuts)
        GContracted.add_edges_from(shortcuts)


def add_shortcuts_to_graph(graph: DiGraph) -> None:
    """Add shortcuts to graph using CH preprocessing."""
    node_ordering_pq = get_node_ordering(graph)
    edges_before = len(graph.edges())
    print(f"Number of arcs before augmenting the graph: {edges_before}")
    G_contracted = copy.deepcopy(graph)
    while not node_ordering_pq.empty():
        edge_difference, v = node_ordering_pq.get()
        new_edge_diff = get_edge_difference(v, G_contracted)
        if new_edge_diff > edge_difference:
            node_ordering_pq.put((new_edge_diff, v))
            continue
        _contract_node(v, graph, G_contracted)
    edges_after = len(graph.edges())
    print(f"Shortcuts added: {edges_after - edges_before}")


def add_shortcuts(input_data: InstanceParameters, manhattan_graph: DiGraph, taxi_rides: pd.DataFrame,
                  node_based_shortest_paths):
    """Entry point for adding shortcuts based on input conditions."""
    if input_data.add_shortcuts:
        add_shortcuts_to_graph(manhattan_graph)
        node_based_shortest_paths = get_node_based_shortest_paths(taxi_rides, manhattan_graph)
        reduce_graph(manhattan_graph, node_based_shortest_paths)
    return node_based_shortest_paths
