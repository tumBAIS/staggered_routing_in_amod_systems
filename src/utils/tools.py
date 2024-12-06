import json
import jsonpickle
import networkx as nx
from networkx import MultiDiGraph
from networkx.readwrite import json_graph
from typing import TypeVar

K = TypeVar('K')
V = TypeVar('V')


def pairwise(iterable):
    # pairwise('ABCDEFG') → AB BC CD DE EF FG
    iterator = iter(iterable)
    a = next(iterator, None)
    for b in iterator:
        yield a, b
        a = b


def deserialize(file_path) -> MultiDiGraph:
    """Function to deserialize a NetworkX DiGraph from a JSON file."""
    with open(file_path, 'r+') as _file:
        graph = json_graph.adjacency_graph(jsonpickle.decode(_file.read()), directed=True)
    return graph


def serialize(graph, file_path):
    """Function to serialize a NetworkX DiGraph to a prettily-formatted JSON file."""
    if not (isinstance(graph, MultiDiGraph) or isinstance(graph, nx.DiGraph)):
        raise Exception(f'graph has to be an instance of networkx.MultiDiGraph or networkx.DiGraph, '
                        f'while it is instance of {type(graph)}')

    # First, use jsonpickle to serialize the adjacency data of the graph
    serialized_graph = jsonpickle.encode(json_graph.adjacency_data(graph))

    # Then, deserialize it back into a Python object with json.loads
    graph_data = json.loads(serialized_graph)

    # Finally, serialize it again to a JSON string with pretty printing
    pretty_json = json.dumps(graph_data, indent=4)

    with open(file_path, 'w+') as _file:
        _file.write(pretty_json)
