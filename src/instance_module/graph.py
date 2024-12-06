import os
import numpy as np
import networkx as nx
from networkx import DiGraph
from shapely.geometry import Point
import jsonpickle
from networkx.readwrite import json_graph

from input_data import InputData
from instance_module.paths import pairwise


def set_arcs_nominal_travel_times_and_capacities(manhattan_graph, input_data):
    """
    Assigns nominal travel times and capacities to arcs in the Manhattan graph based on
    the speed and max flow allowed specified in the input data.
    """
    print(f"Assigning nominal travel times assuming vehicles traveling at {input_data.speed} kph")

    # Set initial nominal travel time attributes to NaN
    nx.set_edge_attributes(manhattan_graph, float('nan'), 'nominal_travel_time')

    for origin, destination in manhattan_graph.edges():
        distance = manhattan_graph[origin][destination]['length']
        nominal_travel_time = distance * 3.6 / input_data.speed
        manhattan_graph[origin][destination]['nominal_travel_time'] = nominal_travel_time

        # Calculate nominal capacity based on max flow allowed
        nominal_capacity = int(np.ceil(nominal_travel_time / input_data.max_flow_allowed))
        manhattan_graph[origin][destination]['nominal_capacity'] = nominal_capacity


def add_initial_arcs_attributes(manhattan_graph):
    """
    Enhances each arc with attributes indicating its origin and destination coordinates,
    and marks them as 'original' from OpenStreetMap.
    """
    nx.set_edge_attributes(manhattan_graph, 'original', 'type_of_arc')

    for origin, destination in manhattan_graph.edges():
        origin_point = Point(manhattan_graph.nodes[origin]['x'], manhattan_graph.nodes[origin]['y'])
        destination_point = Point(manhattan_graph.nodes[destination]['x'], manhattan_graph.nodes[destination]['y'])

        manhattan_graph[origin][destination].update({
            'origin': origin,
            'destination': destination,
            'coordinates_origin': origin_point,
            'coordinates_destination': destination_point
        })


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


def import_graph(input_data: InputData) -> DiGraph:
    """
    Imports a graph structure from a JSON file located based on the network name provided in input_data.
    """
    network_path = os.path.join(os.path.dirname(__file__), f"../../data/{input_data.network_name}")
    network_file = os.path.join(network_path, "network.json")

    if os.path.exists(network_file):
        graph = DiGraph(deserialize_graph(network_file))
        print(f"Loaded {input_data.network_name} network")
    else:
        raise RuntimeError(f"{input_data.network_name} network not found")

    add_initial_arcs_attributes(graph)
    return graph
