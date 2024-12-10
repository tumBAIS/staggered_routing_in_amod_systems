import os
import numpy as np
import networkx as nx
from networkx import DiGraph
from shapely.geometry import Point
import jsonpickle
from networkx.readwrite import json_graph

from input_data import InstanceParameters
from instance_module.paths import pairwise
from input_data import SPEED_KPH


def set_arcs_nominal_travel_times_and_capacities(manhattan_graph, input_data):
    """
    Assigns nominal travel times and capacities to arcs in the Manhattan graph based on
    the speed and max flow allowed specified in the input data.
    """
    print(f"Assigning nominal travel times assuming vehicles traveling at {SPEED_KPH} kph")

    # Set initial nominal travel time attributes to NaN
    nx.set_edge_attributes(manhattan_graph, float('nan'), 'nominal_travel_time')

    for origin, destination in manhattan_graph.edges():
        distance = manhattan_graph[origin][destination]['length']
        nominal_travel_time = distance * 3.6 / SPEED_KPH
        manhattan_graph[origin][destination]['nominal_travel_time'] = nominal_travel_time

        # Calculate nominal capacity based on max flow allowed
        nominal_capacity = int(np.ceil(nominal_travel_time / input_data.max_flow_allowed))
        manhattan_graph[origin][destination]['nominal_capacity'] = nominal_capacity


def reduce_graph(manhattan_graph: DiGraph, node_based_shortest_paths: list[list[int]]):
    """
    Prunes the Manhattan graph by removing nodes and arcs not utilized in node-based shortest paths.
    """
    nodes_utilized = {node for path in node_based_shortest_paths for node in path}
    nodes_to_remove = [node for node in manhattan_graph if node not in nodes_utilized]
    manhattan_graph.remove_nodes_from(nodes_to_remove)

    arcs_utilized = {(u, v) for path in node_based_shortest_paths for u, v in pairwise(path)}
    arcs_to_remove = [arc for arc in manhattan_graph.edges() if arc not in arcs_utilized]
    manhattan_graph.remove_edges_from(arcs_to_remove)

    print(f"Arcs remaining in network: {len(manhattan_graph.edges())}")


def deserialize_graph(file_path: str) -> DiGraph:
    """
    Deserializes a NetworkX DiGraph from a JSON file using jsonpickle and json_graph.
    """
    with open(file_path, 'r') as file:
        graph_data = jsonpickle.decode(file.read())
        return json_graph.adjacency_graph(graph_data, directed=True)


def import_graph(instance_params: InstanceParameters) -> DiGraph:
    """
    Imports a graph structure from a JSON file located based on the network name provided in input_data.
    """
    if os.path.exists(instance_params.path_to_G):
        graph = DiGraph(deserialize_graph(instance_params.path_to_G))
        print(f"Loaded {instance_params.network_name} network")
    else:
        raise RuntimeError(f"{instance_params.network_name} network not found in {instance_params.path_to_G}")

    return graph
