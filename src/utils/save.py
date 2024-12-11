from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from input_data import SolverParameters
from instance_module.instance import Instance
from utils.classes import CompleteSolution, OptimizationMeasures


def transform_path_to_string(path: Path) -> str:
    """
    Transforms the portion of the path after 'data/' into a string
    where '/' or '\\' is replaced by '_'.
    """
    try:
        path_str = str(path)
        split_marker = f"data{os.path.sep}"
        after_data = path_str.split(split_marker, 1)[1]
        transformed = after_data.replace("/", "_").replace("\\", "_").replace("manhattan_", "MAN")
        return transformed
    except IndexError:
        raise ValueError(f"'data{os.path.sep}' not found in path {path_str}.")


def save_experiment(instance: Instance, status_quo: CompleteSolution,
                    solution: CompleteSolution, solver_params: SolverParameters,
                    optimization_measures_list: list[OptimizationMeasures]):
    """
    Save experiment results to JSON files.

    Args:
        instance: The instance object containing problem data.
        status_quo: The initial baseline solution.
        solution: The optimized solution.
        solver_params: Solver parameters.
        optimization_measures_list: List of optimization measures.
    """
    path_to_results = solver_params.path_to_results

    # Prepare instance data for saving
    instance_parameters_to_save = instance.input_data.__dict__.copy()

    # Save the path to the network file (path_to_G) before removing it
    path_to_G = instance_parameters_to_save.get("path_to_G")

    # Remove the 'binaries' fields from status_quo and solution
    if hasattr(status_quo, "binaries"):
        status_quo.binaries = None
    if hasattr(solution, "binaries"):
        solution.binaries = None

    # Round numerical values for cleaner output
    for i in range(len(status_quo.congested_schedule)):
        _round_instance_data(instance, status_quo, solution, i)

    # Remove unnecessary attributes from instance data
    instance_data_to_save = instance.__dict__.copy()
    _remove_unnecessary_instance_columns(instance_data_to_save)

    # Prepare solver parameters for saving
    solver_parameters_to_save = solver_params.__dict__.copy()
    solver_parameters_to_save.pop("instance_parameters", None)
    solver_parameters_to_save.pop("path_to_results", None)

    # Construct output data dictionary
    output_data = {
        "instance_parameters": instance_parameters_to_save,
        "solver_parameters": solver_parameters_to_save,
        "instance": instance_data_to_save,
        "status_quo": status_quo.__dict__,
        "solution": solution.__dict__,
        "optimization_measures_list": [getattr(x, '__dict__', x) for x in optimization_measures_list]
    }

    # Remove paths from input data
    _remove_unnecessary_input_paths(output_data)

    # Save results to JSON
    os.makedirs(path_to_results, exist_ok=True)
    with open(path_to_results / "results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)

    # Save additional files if part of a set of experiments
    if solver_params.set_of_experiments:
        set_of_experiments_path = Path(
            __file__).parent.parent.parent / f"sets_of_experiments/{solver_params.set_of_experiments}"
        experiment_name = transform_path_to_string(path_to_results)
        os.makedirs(set_of_experiments_path / "results" / experiment_name, exist_ok=True)
        os.makedirs(set_of_experiments_path / "networks", exist_ok=True)

        # Copy the file to the target location
        file_name = (
            output_data["instance_parameters"]["network_name"] + "_with_shortcuts.json"
            if output_data["instance_parameters"]["add_shortcuts"]
            else output_data["instance_parameters"]["network_name"] + "_no_shortcuts.json"
        )

        if path_to_G:  # Ensure path_to_G is not None
            shutil.copy(path_to_G, set_of_experiments_path / "networks" / file_name)
        else:
            print("Warning: path_to_G is missing. Network file was not copied.")

        with open(set_of_experiments_path / "results" / experiment_name / "results.json", "w",
                  encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=3)


def _round_instance_data(instance, status_quo, solution, i):
    """Round numerical data in the instance, status quo, and solution for cleaner output."""
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


def _remove_unnecessary_instance_columns(instance_data_to_save):
    """Remove unnecessary attributes from instance data."""
    columns_to_remove = [
        "input_data", "capacities_arcs", "release_times_dataset", "arrival_times_dataset",
        "undivided_conflicting_sets", "latest_departure_times", "earliest_departure_times",
        "min_delay_on_arc", "max_delay_on_arc",
    ]
    for col in columns_to_remove:
        instance_data_to_save.pop(col, None)

    for i in range(len(instance_data_to_save["travel_times_arcs"])):
        instance_data_to_save["travel_times_arcs"][i] = round(instance_data_to_save["travel_times_arcs"][i], 2)


def _remove_unnecessary_input_paths(output_data):
    """Remove unnecessary path attributes from input data."""
    columns_to_remove = ["path_to_G", "path_to_routes", "path_to_instance"]
    for col in columns_to_remove:
        output_data["instance_parameters"].pop(col, None)


def _save_to_set_of_experiments(output_data, solver_params, path_to_results):
    """Save experiment data to a designated set of experiments directory."""
    set_of_experiments_path = Path(
        __file__).parent.parent.parent / f"sets_of_experiments/{solver_params.set_of_experiments}"
    experiment_name = transform_path_to_string(path_to_results)
    os.makedirs(set_of_experiments_path / "results" / experiment_name, exist_ok=True)
    os.makedirs(set_of_experiments_path / "networks", exist_ok=True)

    # Determine file name based on shortcuts
    file_name = (
        output_data["instance_parameters"]["network_name"] + "_with_shortcuts.json"
        if output_data["instance_parameters"]["add_shortcuts"]
        else output_data["instance_parameters"]["network_name"] + "_no_shortcuts.json"
    )
    shutil.copy(output_data["instance_parameters"]["path_to_G"], set_of_experiments_path / "networks" / file_name)

    with open(set_of_experiments_path / "results" / experiment_name / "results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)
