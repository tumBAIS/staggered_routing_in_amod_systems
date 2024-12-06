from __future__ import annotations

import json
import os
import sys
import pickle
import typing
from dataclasses import dataclass

import shapely

from instanceModule.instance import Instance
from utils.classes import CompleteSolution, OptimizationMeasures


def linestring_to_dict(linestring):
    """
    Transform a LineString into a dictionary format.

    Args:
        linestring (LineString): The LineString object to transform.

    Returns:
        dict: A dictionary representing the LineString.
    """
    if not isinstance(linestring, shapely.LineString):
        return linestring

    # Extract the type and coordinates from the LineString
    geom_dict = {
        "type": "LineString",
        "coordinates": list(linestring.coords)
    }

    return geom_dict


def save_experiment(inputSource: str, instance: Instance, statusQuo: CompleteSolution, solution: CompleteSolution):
    path_to_results = instance.input_data.path_to_results
    # Create a Pandas DataFrame with data from different classes
    inputData_to_save = instance.input_data.__dict__
    for arc, _ in enumerate(instance.osm_info_arcs_utilized):
        if arc > 0:
            instance.osm_info_arcs_utilized[arc] = linestring_to_dict(
                instance.osm_info_arcs_utilized[arc]["geometry"])
    statusQuo.binaries = {}
    solution.binaries = {}

    for i in range(len(statusQuo.congested_schedule)):
        instance.max_staggering_applicable[i] = round(instance.max_staggering_applicable[i], 2)
        instance.deadlines[i] = round(instance.deadlines[i], 2)
        statusQuo.release_times[i] = round(statusQuo.release_times[i], 2)
        statusQuo.staggering_applicable[i] = round(statusQuo.staggering_applicable[i], 2)
        statusQuo.staggering_applied[i] = round(statusQuo.staggering_applied[i], 2)
        solution.release_times[i] = round(solution.release_times[i], 2)
        solution.staggering_applicable[i] = round(solution.staggering_applicable[i], 2)
        solution.staggering_applied[i] = round(solution.staggering_applied[i], 2)

        for j in range(len(statusQuo.congested_schedule[i])):
            statusQuo.congested_schedule[i][j] = round(statusQuo.congested_schedule[i][j], 2)
            statusQuo.free_flow_schedule[i][j] = round(statusQuo.free_flow_schedule[i][j], 2)
            statusQuo.delays_on_arcs[i][j] = round(statusQuo.delays_on_arcs[i][j], 2)
            solution.congested_schedule[i][j] = round(solution.congested_schedule[i][j], 2)
            solution.free_flow_schedule[i][j] = round(solution.free_flow_schedule[i][j], 2)
            solution.delays_on_arcs[i][j] = round(solution.delays_on_arcs[i][j], 2)

    instance_data_to_save = instance.__dict__
    cols_to_delete = ["input_data", "capacities_arcs", "release_times_dataset", "arrival_times_dataset",
                      "undivided_conflicting_sets", "latest_departure_times", "earliest_departure_times",
                      "min_delay_on_arc", "max_delay_on_arc"]
    for col in cols_to_delete:
        del instance_data_to_save[col]
    for i in range(len(instance_data_to_save["travel_times_arcs"])):
        instance_data_to_save["travel_times_arcs"][i] = \
            round(instance_data_to_save["travel_times_arcs"][i], 2)

    output_data = {
        "input_data": inputData_to_save,
        'instance': instance_data_to_save,
        'statusQuo': statusQuo.__dict__,
        'solution': solution.__dict__,
    }

    cols_input_data_to_delete = ["path_to_G", "path_to_routes", "path_to_instance", "path_to_results"]
    for col in cols_input_data_to_delete:
        del output_data["input_data"][col]

    # Create directory to save results
    os.makedirs(path_to_results, exist_ok=True)

    with open(path_to_results / "results.json", 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)

    # save twice on cluster
    if inputSource == "console":
        pathToResults = sys.argv[2]
        with open(f'{pathToResults}/results.p', 'wb') as pickle_file:
            pickle.dump(output_data, pickle_file)

    return


@dataclass
class InitialOutputData:
    instance: Instance
    status_quo: CompleteSolution
    warm_start: CompleteSolution

    def save_output(self, machine: str) -> None:
        if machine == "local":
            path_to_data = os.path.join(os.path.dirname(__file__), "../../results")
        else:
            path_to_data = sys.argv[2]
        with open(f"{path_to_data}/instance_file.p", "wb") as outfile:
            pickle.dump(self, outfile)
        return


@dataclass
class FinalOutputData:
    instance: Instance
    status_quo: CompleteSolution
    warm_start: CompleteSolution
    model_solution: CompleteSolution
    optimization_measures: OptimizationMeasures
    random_solution: CompleteSolution
    mapped_system: typing.Any

    def save_output(self, machine: str) -> None:
        if machine == "local":
            path_to_data = os.path.join(os.path.dirname(__file__), "../../results")
        else:
            path_to_data = sys.argv[2]
        with open(f"{path_to_data}/final_experimental_results.p", "wb") as outfile:
            pickle.dump(self, outfile)
        return
