import networkx as nx
import numpy as np
import os
import shapely

import inputData
from instanceModule.paths import pairwise
from networkx import DiGraph
import jsonpickle
from networkx.readwrite import json_graph

from shapely.geometry import LineString


def setArcsNominalTravelTimesAndCapacities(manhattanGraph, inputData):
    """
    Assigns nominal travel times and capacities to arcs in the Manhattan graph.

    """

    print(f"Assigning nominal travel times assuming vehicles traveling at {inputData.speed} kph")

    # Set initial nominal travel time attributes to NaN
    nx.set_edge_attributes(manhattanGraph, float('nan'), "nominal_travel_time")

    for origin, destination in manhattanGraph.edges():
        # Calculate nominal travel time in seconds
        nominalTravelTimeArc = manhattanGraph[origin][destination]['length'] * 3.6 / inputData.speed
        manhattanGraph[origin][destination]['nominal_travel_time'] = (nominalTravelTimeArc)

        # Calculate nominal capacity based on max flow allowed
        nominalCapacityArc = int(
            np.ceil(manhattanGraph[origin][destination]["nominal_travel_time"] / inputData.maxFlowAllowed))
        manhattanGraph[origin][destination]["nominal_capacity"] = nominalCapacityArc

    return


def _addInitialArcsAttributes(manhattanGraph):
    """
    Adds to the arcs the following attributes: original (obtained from OSM), arc origin and destination ,
    coordinates of origin and destination of the arc (x and y)
    """

    nx.set_edge_attributes(manhattanGraph, "original", "typeOfArc")

    for origin, destination in manhattanGraph.edges:
        manhattanGraph[origin][destination]["origin"] = origin
        manhattanGraph[origin][destination]["destination"] = destination

        origin_coords = shapely.Point(manhattanGraph.nodes[origin]["x"], manhattanGraph.nodes[origin]["y"])
        dest_coords = shapely.Point(manhattanGraph.nodes[destination]["x"], manhattanGraph.nodes[destination]["y"])

        manhattanGraph[origin][destination]["coordinates_origin"] = origin_coords
        manhattanGraph[origin][destination]["coordinates_destination"] = dest_coords


def reduceGraph(manhattanGraph: DiGraph, nodeBasedShortestPaths: list[list[int]], inputData):
    """
    Removes from Manhattan graph nodes and arcs not utilized in node based shortest paths.

    """

    nodes_utilized = set(node for path in nodeBasedShortestPaths for node in path)
    nodes_to_remove = [node for node in manhattanGraph if node not in nodes_utilized]
    manhattanGraph.remove_nodes_from(nodes_to_remove)

    arcs_utilized = {(u, v) for path in nodeBasedShortestPaths for u, v in pairwise(path)}
    arcs_to_remove = [arc for arc in manhattanGraph.edges() if arc not in arcs_utilized]
    manhattanGraph.remove_edges_from(arcs_to_remove)

    print(f"Arcs original network: {len(manhattanGraph.edges)}")


# https://gist.github.com/nuthanmunaiah/523a5e112f1e1f458e2c
def _deserialize(file_path):
    '''Function to _deserialize a NetworkX DiGraph from a JSON file.'''
    with open(file_path, 'r+') as _file:
        call_graph = json_graph.adjacency_graph(jsonpickle.decode(_file.read()), directed=True)
    return call_graph


def import_graph(input_data: inputData.InputData) -> DiGraph:
    pathToInstances = os.path.join(os.path.dirname(__file__), f"../../data/{input_data.network_name}")
    if os.path.exists(f"{pathToInstances}/network.json"):
        graph = DiGraph(_deserialize(f"{pathToInstances}/network.json"))
        print(f"Loaded {input_data.network_name} network")
    else:
        raise RuntimeError(f"{input_data.network_name} network not found")
    _addInitialArcsAttributes(graph)
    return graph
