from __future__ import annotations

from processing.shortcuts import add_shortcuts
from instanceModule.graph import import_graph, reduce_graph, set_arcs_nominal_travel_times_and_capacities
from instanceModule.instance import Instance, get_instance, print_total_free_flow_time
from instanceModule.paths import get_arc_based_paths_with_features
from instanceModule.rides import import_trips_df
from inputData import InputData


def get_not_simplified_instance(inputData: InputData) -> Instance:
    trips_df = import_trips_df(inputData)
    graph = import_graph(inputData)
    reduce_graph(graph, trips_df["path"], inputData)
    node_based_shortest_paths = add_shortcuts(inputData, graph, trips_df, trips_df["path"])
    set_arcs_nominal_travel_times_and_capacities(graph, inputData)

    arc_based_shortest_paths, arcs_features = get_arc_based_paths_with_features(node_based_shortest_paths, graph)
    instance = get_instance(inputData, arc_based_shortest_paths, arcs_features, trips_df["release_time"].to_list(),
                            trips_df["deadline"].to_list())

    print_total_free_flow_time(instance)
    instance.set_deadlines(trips_df["deadline"].to_list())
    instance.set_max_staggering_applicable()
    instance.check_optional_fields()
    return instance
