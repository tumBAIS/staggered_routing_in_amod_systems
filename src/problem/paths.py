from itertools import tee
import networkx as nx
from networkx import DiGraph
from pandas import DataFrame
from typing import Any


def pairwise(iterable):
    """
    Generates a pairwise iterator from the given iterable.

    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def get_arc_based_shortest_paths_original_ids(node_based_shortest_paths: list[list[int]]) -> list[
    list[tuple[int, int]]]:
    """
    Converts node-based paths to arc-based paths using original node IDs.

    """
    return [[(u, v) for u, v in pairwise(path)] for path in node_based_shortest_paths]


def remove_repetitions(seq: list) -> list:
    """
    Removes duplicate entries in a list while maintaining order.

    """
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def get_arcs_utilized_ids(arc_based_shortest_paths_original_ids: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    """
    Extracts a list of unique arcs used across all paths.

    """
    arcs_with_repetitions = [arc for path in arc_based_shortest_paths_original_ids for arc in path]
    return remove_repetitions(arcs_with_repetitions)


def map_arc_based_shortest_paths(
        arc_based_shortest_paths_original_ids: list[list[tuple[int, int]]],
        arcs_utilized_ids: list[tuple[int, int]],
) -> list[list[int]]:
    """
    Maps arcs to their indices in the utilized list, adding a dummy sink arc.

    """
    arc_based_shortest_paths = [
        [arcs_utilized_ids.index(arc) + 1 for arc in path] for path in arc_based_shortest_paths_original_ids
    ]
    for path in arc_based_shortest_paths:
        path.append(0)  # Adding a final dummy edge representing the sink
    return arc_based_shortest_paths


def get_travel_times_arcs_utilized(manhattan_graph: DiGraph, arcs_utilized_ids: list[tuple[int, int]]) -> list[float]:
    """
    Retrieves the travel times for utilized arcs, adding a zero at the start for the dummy node.

    """
    travel_times = [manhattan_graph[origin][destination]["nominal_travel_time"] for origin, destination in
                    arcs_utilized_ids]
    travel_times.insert(0, 0)
    return travel_times


def get_nominal_capacity_arcs_utilized(manhattan_graph: DiGraph, arcs_utilized_ids: list[tuple[int, int]]) -> list[int]:
    """
    Retrieves the nominal capacities for utilized arcs, adding a zero at the start for the dummy node.

    """
    capacities = [manhattan_graph[origin][destination]["nominal_capacity"] for origin, destination in arcs_utilized_ids]
    capacities.insert(0, 0)
    return capacities


def get_arc_based_paths_with_features(
        node_based_shortest_paths: list[list[int]], manhattan_graph: DiGraph
) -> tuple[list[list[int]], list[float], list[int]]:
    """
    Combines arc paths with feature extraction for nominal capacities and travel times.
    """
    arc_based_shortest_paths_original_ids = get_arc_based_shortest_paths_original_ids(node_based_shortest_paths)
    arcs_utilized_ids = get_arcs_utilized_ids(arc_based_shortest_paths_original_ids)
    arc_based_shortest_paths = map_arc_based_shortest_paths(arc_based_shortest_paths_original_ids, arcs_utilized_ids)
    travel_times_arcs_utilized = get_travel_times_arcs_utilized(manhattan_graph, arcs_utilized_ids)
    nominal_capacities_arcs = get_nominal_capacity_arcs_utilized(manhattan_graph, arcs_utilized_ids)
    return arc_based_shortest_paths, travel_times_arcs_utilized, nominal_capacities_arcs
