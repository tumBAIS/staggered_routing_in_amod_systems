from __future__ import annotations

import json
import os
import shutil
import sys
import pickle
import typing
from dataclasses import dataclass
from pathlib import Path
import shapely

from input_data import SolverParameters
from instance_module.instance import Instance
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

    return {
        "type": "LineString",
        "coordinates": list(linestring.coords),
    }


def transform_path_to_string(path: Path) -> str:
    """
    Transforms the portion of the path after 'data/' into a string
    where '/' or '\\' is replaced by '_'.

    Args:
        path (Path): The full path object.

    Returns:
        str: Transformed string.
    """
    try:
        path_str = str(path)
        split_marker = f"data{os.path.sep}"
        after_data = path_str.split(split_marker, 1)[1]
        transformed = after_data.replace("/", "_").replace("\\", "_")
        transformed = transformed.replace("manhattan_", "MAN")
        return transformed
    except IndexError:
        raise ValueError(f"'data{os.path.sep}' not found in path {path_str}.")


def save_experiment(instance: Instance, status_quo: CompleteSolution,
                    solution: CompleteSolution, solver_params: SolverParameters,
                    optimization_measures_list: list[OptimizationMeasures]):
    """
    Save experiment results to JSON files.

    Args:
        input_source (str): Input source identifier.
        instance (Instance): Instance data.
        status_quo (CompleteSolution): Baseline solution data.
        solution (CompleteSolution): Optimized solution data.
        solver_params (SolverParameters): Solver parameters.
    """
    path_to_results = solver_params.path_to_results

    # Process instance data
    instance_parameters_to_save = instance.input_data.__dict__
    for arc, _ in enumerate(instance.osm_info_arcs_utilized):
        if arc > 0:
            instance.osm_info_arcs_utilized[arc] = linestring_to_dict(
                instance.osm_info_arcs_utilized[arc]["geometry"]
            )

    # Clear unnecessary data
    status_quo.binaries = {}
    solution.binaries = {}

    for i in range(len(status_quo.congested_schedule)):
        instance.max_staggering_applicable[i] = round(instance.max_staggering_applicable[i], 2)
        instance.deadlines[i] = round(instance.deadlines[i], 2)
        status_quo.release_times[i] = round(status_quo.release_times[i], 2)
        status_quo.staggering_applicable[i] = round(status_quo.staggering_applicable[i], 2)
        status_quo.staggering_applied[i] = round(status_quo.staggering_applied[i], 2)
        solution.release_times[i] = round(solution.release_times[i], 2)
        solution.staggering_applicable[i] = round(solution.staggering_applicable[i], 2)
        solution.staggering_applied[i] = round(solution.staggering_applied[i], 2)

        for j in range(len(status_quo.congested_schedule[i])):
            status_quo.congested_schedule[i][j] = round(status_quo.congested_schedule[i][j], 2)
            status_quo.free_flow_schedule[i][j] = round(status_quo.free_flow_schedule[i][j], 2)
            status_quo.delays_on_arcs[i][j] = round(status_quo.delays_on_arcs[i][j], 2)
            solution.congested_schedule[i][j] = round(solution.congested_schedule[i][j], 2)
            solution.free_flow_schedule[i][j] = round(solution.free_flow_schedule[i][j], 2)
            solution.delays_on_arcs[i][j] = round(solution.delays_on_arcs[i][j], 2)

    instance_data_to_save = instance.__dict__
    cols_to_delete = [
        "input_data", "capacities_arcs", "release_times_dataset", "arrival_times_dataset",
        "undivided_conflicting_sets", "latest_departure_times", "earliest_departure_times",
        "min_delay_on_arc", "max_delay_on_arc",
    ]
    for col in cols_to_delete:
        instance_data_to_save.pop(col, None)

    for i in range(len(instance_data_to_save["travel_times_arcs"])):
        instance_data_to_save["travel_times_arcs"][i] = round(instance_data_to_save["travel_times_arcs"][i], 2)

    solver_parameters_to_save = solver_params.__dict__
    solver_parameters_to_save.pop("instance_parameters", None)
    solver_parameters_to_save.pop("path_to_results", None)

    output_data = {
        "instance_parameters": instance_parameters_to_save,
        "solver_parameters": solver_parameters_to_save,
        "instance": instance_data_to_save,
        "status_quo": status_quo.__dict__,
        "solution": solution.__dict__,
        "optimization_measures_list": [getattr(x, '__dict__', x) for x in optimization_measures_list]
    }

    path_to_G = output_data["instance_parameters"]["path_to_G"]

    cols_input_data_to_delete = ["path_to_G", "path_to_routes", "path_to_instance"]
    for col in cols_input_data_to_delete:
        output_data["instance_parameters"].pop(col, None)

    # Save results to directory
    os.makedirs(path_to_results, exist_ok=True)

    with open(path_to_results / "results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)

    if solver_params.set_of_experiments:
        path_to_set_of_experiments = Path(
            __file__).parent.parent.parent / f"sets_of_experiments/{solver_params.set_of_experiments}"
        experiment_name = transform_path_to_string(path_to_results)
        os.makedirs(path_to_set_of_experiments / "results" / experiment_name, exist_ok=True)
        os.makedirs(path_to_set_of_experiments / "networks", exist_ok=True)
        # Copy the file to the target location
        file_name = (
            output_data["instance_parameters"]["network_name"] + "_with_shortcuts.json"
            if output_data["instance_parameters"]["add_shortcuts"]
            else output_data["instance_parameters"]["network_name"] + "_no_shortcuts.json"
        )

        shutil.copy(path_to_G, path_to_set_of_experiments / "networks" / file_name)
        with open(path_to_set_of_experiments / "results" / experiment_name / "results.json", "w",
                  encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=3)


@dataclass
class InitialOutputData:
    instance: Instance
    status_quo: CompleteSolution
    warm_start: CompleteSolution

    def save_output(self, machine: str) -> None:
        path_to_data = (
            os.path.join(os.path.dirname(__file__), "../../results") if machine == "local" else sys.argv[2]
        )
        with open(f"{path_to_data}/instance_file.p", "wb") as outfile:
            pickle.dump(self, outfile)


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
        path_to_data = (
            os.path.join(os.path.dirname(__file__), "../../results") if machine == "local" else sys.argv[2]
        )
        with open(f"{path_to_data}/final_experimental_results.p", "wb") as outfile:
            pickle.dump(self, outfile)
