import json

import jsonpickle
import networkx as nx
from networkx import MultiDiGraph
from networkx.readwrite import json_graph

import cpp_module as cpp

from inputData import CONSTR_TOLERANCE, TOLERANCE
import random
from typing import TypeVar

K = TypeVar('K')
V = TypeVar('V')


def remove_duplicates(lst):
    seen = set()
    new_lst = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            new_lst.append(item)
    return new_lst


def pairwise(iterable):
    # pairwise('ABCDEFG') → AB BC CD DE EF FG
    iterator = iter(iterable)
    a = next(iterator, None)
    for b in iterator:
        yield a, b
        a = b


def key_with_max_value(d: dict[K, V]) -> K:
    if not d:
        raise ValueError("no dict provided")
    return max(d, key=d.get)


def sort_keys_by_value(d: dict[K, V]) -> list[K]:
    return sorted(d, key=d.get, reverse=True)


def assert_similar_lists(list1, list2, tolerance=1e-4):
    try:
        assert len(list1) == len(list2), "The lists have different numbers of sublists"

        for sublist1, sublist2 in zip(list1, list2):
            assert len(sublist1) == len(sublist2), "Sublists have different lengths"

            for value1, value2 in zip(sublist1, sublist2):
                assert abs(
                    value1 - value2) <= tolerance, f"Values {value1} and {value2} differ by more than {tolerance}"
    except:
        AssertionError("lists have different lengths")


def assert_similar_dictionaries(dict1, dict2, tolerance=1e-4):
    assert dict1.keys() == dict2.keys(), "Dictionaries have different keys"  # order doesn't matter

    for key in dict1:
        list1 = dict1[key]
        list2 = dict2[key]
        assert len(list1) == len(list2), f"Lists for key {key} have different lengths"

        for value1, value2 in zip(list1, list2):
            try:
                assert abs(value1 - value2) <= tolerance, (
                    f"Values {value1} and {value2} at key {key} differ by more than {tolerance}"
                )
            except:
                raise AssertionError


def is_distant(value, values_list, min_distance=CONSTR_TOLERANCE) -> bool:
    for item in values_list:
        if abs(round(value, 6) - round(item, 6)) < min_distance - TOLERANCE:
            return False  # Found a value too close to 'value'
    return True  # All values are at least 'min_distance' away from 'value'


def random_bool(probability: float) -> bool:
    """
    Returns True with the specified small probability and False otherwise.

    :param probability: The probability of returning True, should be a small value (e.g., 0.01 for 1%).
    :return: True with the given probability, False otherwise.
    """
    return random.random() < probability


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


def print_improvements_solution(status_quo: cpp.cpp_solution, solution: cpp.cpp_solution, trips,
                                solution_name: str):
    border = "=" * 60

    # Print solution info for both status quo and the new solution
    num_trip_controlled = sum(trips.controlled_flags)
    solution.print_solution_info(num_trip_controlled, name=solution_name)

    # Print the header for solution improvements
    print(f"\n{border}")
    print(f"{'SOLUTION IMPROVEMENT':^60}")
    print(f"{border}\n")

    # Calculate reductions in metrics
    travel_time_reduction = _calculate_percentage_reduction(status_quo.get_total_travel_time(),
                                                            solution.get_total_travel_time())
    total_delay_reduction = _calculate_percentage_reduction(status_quo.get_total_delay(), solution.get_total_delay())
    congestion_delay_reduction = _calculate_percentage_reduction(status_quo.get_congestion_delay(),
                                                                 solution.get_congestion_delay())

    # Print total metrics improvements
    print(f"{'TOTAL METRICS':^60}")
    print(f"{'Travel Time Reduction:':<40} {travel_time_reduction:.2f}%")
    print(f"{'Total Delay Reduction:':<40} {total_delay_reduction:.2f}%")
    print(f"{'Congestion Delay Reduction:':<40} {congestion_delay_reduction:.2f}%\n")

    # Calculate reductions in controlled metrics
    travel_time_controlled_reduction = _calculate_percentage_reduction(status_quo.get_total_travel_time_controlled(),
                                                                       solution.get_total_travel_time_controlled())
    total_delay_controlled_reduction = _calculate_percentage_reduction(status_quo.get_total_delay_controlled(),
                                                                       solution.get_total_delay_controlled())
    congestion_delay_controlled_reduction = _calculate_percentage_reduction(
        status_quo.get_congestion_delay_controlled(),
        solution.get_congestion_delay_controlled())

    # Print controlled metrics improvements
    print(f"{'CONTROLLED METRICS':^60}")
    print(f"{'Travel Time Controlled Reduction:':<40} {travel_time_controlled_reduction:.2f}%")
    print(f"{'Total Delay Controlled Reduction:':<40} {total_delay_controlled_reduction:.2f}%")
    print(f"{'Congestion Delay Controlled Reduction:':<40} {congestion_delay_controlled_reduction:.2f}%")

    print(f"\n{border}")
    print(f"{'END OF SOLUTION IMPROVEMENT':^60}")
    print(f"{border}\n")


def _calculate_percentage_reduction(old_value, new_value):
    if old_value == 0:
        return 0
    return ((old_value - new_value) / old_value) * 100
