from __future__ import annotations

from queue import PriorityQueue

import pandas as pd
import shapely
from shapely import Point
import networkx as nx

from networkx import DiGraph
import copy

from instanceModule.graph import reduce_graph
from instanceModule.paths import getNodeBasedShortestPaths
from inputData import InputData


def _getIncidentArcs(v: int, G: DiGraph) -> (list[tuple[int, int, dict]],
                                             list[tuple[int, int, dict]]):
    """
    Return incident arcs of v
    """
    inEdges = list(G.in_edges(v, data=True))[:]
    outEdges = list(G.out_edges(v, data=True))[:]
    return inEdges, outEdges


def _isolateNode(G: DiGraph,
                 inEdges: list[tuple[int, int, dict]],
                 outEdges: list[tuple[int, int, dict]]) -> None:
    G.remove_edges_from(inEdges)
    G.remove_edges_from(outEdges)


def _getLengthsIncidentArcs(inArcs: list[tuple[int, int, dict]],
                            outArcs: list[tuple[int, int, dict]]) -> (dict[int:float], dict[int:float]):
    inArcsLengths = {u: data["length"] for u, _, data in inArcs}
    outArcsLengths = {w: data["length"] for _, w, data in outArcs}
    return inArcsLengths, outArcsLengths


def getShortcuts(u: int,
                 G: DiGraph,
                 inArcsLengths: dict[int:float],
                 outArcsLengths: dict[int:float]) -> list[tuple[int, int, dict]]:
    Pw = {w: inArcsLengths[u] + outArcsLengths[w] for w in outArcsLengths}  # cost to reach w going through v
    PMax = max(Pw.values())
    distances, _ = nx.single_source_dijkstra(G, source=u, cutoff=PMax,
                                             weight="length")  # v is excluded cause isolated
    wTargets = [target for target in outArcsLengths if target not in distances or distances[target] > Pw[target]]
    shortcuts = [(u, w, {"length": Pw[w],
                         "origin": u,
                         "destination": w,
                         "typeOfArc": "shortcut",
                         "coordinates_origin": Point(G.nodes[u]["x"], G.nodes[u]["y"]),
                         "coordinates_destination": Point(G.nodes[w]["x"], G.nodes[w]["y"]),
                         "geometry": shapely.LineString([Point(G.nodes[u]["x"], G.nodes[u]["y"]),
                                                         Point(G.nodes[w]["x"], G.nodes[w]["y"])])})
                 for w in wTargets]
    return shortcuts


def _restoreGraph(G: DiGraph,
                  allShortcuts: list[tuple[int, int, dict]],
                  inArcs: list[tuple[int, int, dict]],
                  outArcs: list[tuple[int, int, dict]]):
    G.remove_edges_from(allShortcuts)
    G.add_edges_from(inArcs)
    G.add_edges_from(outArcs)


def _getEdgeDifference(v: int, graph: DiGraph) -> int:
    inArcs, outArcs = _getIncidentArcs(v, graph)
    numIncidentEdges = len(inArcs) + len(outArcs)
    if not inArcs or not outArcs:
        return 0
    inArcsLengths, outArcsLengths = _getLengthsIncidentArcs(inArcs, outArcs)
    _isolateNode(graph, inArcs, outArcs)
    allShortcuts = []
    for u in inArcsLengths:
        shortcuts = getShortcuts(u, graph, inArcsLengths, outArcsLengths)
        graph.add_edges_from(shortcuts)
        allShortcuts.extend(shortcuts)
    _restoreGraph(graph, allShortcuts, inArcs, outArcs)
    edgeDifference = len(allShortcuts) - numIncidentEdges
    return edgeDifference


def _getNodeOrdering(graph: DiGraph) -> PriorityQueue:
    """
    Returns a priority queue with all the nodes of the graph, and whose priority is given by the edge difference
    the edge difference is the number of arcs to add to the graph if node is contracted
    it is computed as the number of shortcuts (we add) - number of incident edges (we remove)
    """
    nodeOrdering = PriorityQueue()
    for v in graph.nodes:
        edgeDifference = _getEdgeDifference(v, graph)
        nodeOrdering.put((edgeDifference, v))
    return nodeOrdering


def _printShortcutsAdded(shortcuts: list[tuple[int, int, dict]]) -> None:
    if shortcuts:
        for u, w, k in shortcuts:
            print(f"Added shortcut from {u} to {w} of len {k['length']}")


def _getMaxContractionLevelIncidentArcs(inArcs: list[tuple[int, int, dict]],
                                        outArcs: list[tuple[int, int, dict]]) -> int:
    inArcsLengths = {u: k["contraction_level"] for u, _, k in inArcs}
    outArcsLengths = {w: k["contraction_level"] for _, w, k in outArcs}
    return max(max(inArcsLengths.values()), max(outArcsLengths.values()))


def _contractNode(v: int, graph: DiGraph, GContracted: DiGraph) -> None:
    """
    contract node v on GContracted, obtain the relative shortcuts and add them both to GContracted and graph

    """
    inArcs, outArcs = _getIncidentArcs(v, GContracted)
    if not inArcs or not outArcs:
        return
    inArcsLengths, outArcsLengths = _getLengthsIncidentArcs(inArcs, outArcs)
    GContracted.remove_node(v)
    for u in inArcsLengths:
        shortcuts = getShortcuts(u, GContracted, inArcsLengths, outArcsLengths)
        graph.add_edges_from(shortcuts)
        GContracted.add_edges_from(shortcuts)


def _has_isolated_nodes(graph):
    isolated_nodes = [node for node in graph.nodes if graph.degree(node) == 0]
    return len(isolated_nodes) > 0


def _addShortcutsToGraph(graph: DiGraph) -> None:
    """
    Add shortcuts to graph according to CH preprocessing
    """
    nodeOrderingPQ = _getNodeOrdering(graph)
    edgesBefore = len(graph.edges())
    print(f"Number of arcs before augmenting the graph: {edgesBefore}")
    GContracted = copy.deepcopy(graph)
    while not nodeOrderingPQ.empty():
        edgeDifference, v = nodeOrderingPQ.get()
        newEdgeDiff = _getEdgeDifference(v, GContracted)
        lazyUpdateCondition1 = newEdgeDiff > edgeDifference
        lazyUpdateCondition2 = not nodeOrderingPQ.empty() and newEdgeDiff > nodeOrderingPQ.queue[0][0]
        if lazyUpdateCondition1 and lazyUpdateCondition2:
            nodeOrderingPQ.put((newEdgeDiff, v))
            continue
        _contractNode(v, graph, GContracted)
    edgesAfter = len(graph.edges())
    print(f"Shortcuts added: {edgesAfter - edgesBefore}")


def add_shortcuts(inputData: InputData, manhattanGraph: DiGraph, taxiRides: pd.Dataframe,
                  nodeBasedShortestPaths):
    if inputData.add_shortcuts:
        _addShortcutsToGraph(manhattanGraph)
        nodeBasedShortestPaths = getNodeBasedShortestPaths(taxiRides, manhattanGraph)
        reduce_graph(manhattanGraph, nodeBasedShortestPaths, inputData)
    return nodeBasedShortestPaths
