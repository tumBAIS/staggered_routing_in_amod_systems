import os
import numpy as np
import networkx as nx
from networkx import DiGraph
import jsonpickle
from networkx.readwrite import json_graph
from input_data import InstanceParameters
from input_data import SPEED_KPH


def set_arcs_nominal_travel_times_and_capacities(graph: nx.DiGraph, instance_params: InstanceParameters) -> None:
    """
    Assigns nominal travel times and capacities to arcs in the Manhattan graph based on
    the speed and max flow allowed specified in the input data.
    """
    print(f"Assigning nominal travel times assuming vehicles traveling at {SPEED_KPH} kph")

    # Set initial nominal travel time attributes to NaN
    nx.set_edge_attributes(graph, float('nan'), 'nominal_travel_time')

    for origin, destination in graph.edges():
        distance = graph[origin][destination]['length']
        nominal_travel_time = distance * 3.6 / SPEED_KPH
        graph[origin][destination]['nominal_travel_time'] = nominal_travel_time

        # Calculate nominal capacity based on max flow allowed
        nominal_capacity = int(np.ceil(nominal_travel_time / instance_params.max_flow_allowed))
        graph[origin][destination]['nominal_capacity'] = nominal_capacity


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
