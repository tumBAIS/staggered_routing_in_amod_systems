from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from input_data import SolverParameters
from problem.instance import Instance
from problem.solution import Solution
from typing import Optional


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


def save_experiment(instance: Instance,
                    status_quo: Solution,
                    solver_params: SolverParameters,
                    optimization_measures_list: Optional[list[dict]] = None,
                    solution: Optional[Solution] = None):
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
    instance_parameters_to_save = instance.instance_params.__dict__.copy()

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
    solution_to_save = solution.__dict__ if solution is not None else None
    opt_measures_to_save = [getattr(x, '__dict__', x) for x in
                            optimization_measures_list] if optimization_measures_list is not None else None
    # Construct output data dictionary
    output_data = {
        "instance_parameters": instance_parameters_to_save,
        "solver_parameters": solver_parameters_to_save,
        "instance": instance_data_to_save,
        "status_quo": status_quo.__dict__,
        "solution": solution_to_save,
        "optimization_measures_list": opt_measures_to_save
    }

    # Remove paths from input data
    _remove_unnecessary_input_paths(output_data)

    # Save results to JSON
    os.makedirs(path_to_results, exist_ok=True)
    with open(path_to_results / "results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)

        # Save additional files if part of a set of experiments
        if solver_params.set_of_experiments:
            path_to_instance = instance.instance_params.path_to_instance
            path_to_routes = instance.instance_params.path_to_routes
            sets_of_experiments_name = solver_params.set_of_experiments
            save_results_and_instance_in_set_of_experiments_folder(sets_of_experiments_name,
                                                                   path_to_results,
                                                                   path_to_G,
                                                                   path_to_instance,
                                                                   path_to_routes,
                                                                   output_data)


def save_results_and_instance_in_set_of_experiments_folder(sets_of_experiments_name: str,
                                                           path_to_results: Path,
                                                           path_to_G: Optional[Path],
                                                           path_to_instance: Optional[Path],
                                                           path_to_routes: Optional[Path],
                                                           output_data: dict
                                                           ):
    """
    Save results.json and instance.json in the appropriate set_of_experiments folder,
    and copy the network file if available.
    """

    base_path = Path(__file__).resolve().parents[2] / "sets_of_experiments" / sets_of_experiments_name
    experiment_name = transform_path_to_string(path_to_results)
    result_folder = base_path / "results" / experiment_name
    network_folder = base_path / "networks"

    os.makedirs(result_folder, exist_ok=True)
    os.makedirs(network_folder, exist_ok=True)

    # Determine the filename of the network file
    network_name = output_data["instance_parameters"]["network_name"]
    use_shortcuts = output_data["instance_parameters"].get("add_shortcuts", False)
    network_filename = f"{network_name}_{'with' if use_shortcuts else 'no'}_shortcuts.json"

    def safe_copy_file(src: Path, dst: Path, label: str):
        """Helper"""
        if src and src.exists():
            shutil.copy(src, dst)
            print(f"✅ Copied {label} file to {dst}")
        else:
            print(f"⚠️ Warning: {label} file is missing or does not exist. File was not copied.")

    # Copy files in set_of_experiment_directory
    safe_copy_file(path_to_G, network_folder / network_filename, "network")
    safe_copy_file(path_to_instance, result_folder / "instance.json", "instance")
    safe_copy_file(path_to_routes, result_folder / "routes.json", "routes")

    # Copy the original routes.json
    if path_to_routes and path_to_routes.exists():
        shutil.copy(path_to_routes, result_folder / "routes.json")
    else:
        print("⚠️ Warning: path_to_routes is missing or does not exist. routes.json was not copied.")


def _round_instance_data(instance, status_quo: Solution, solution: Solution, i):
    """Round numerical data in the instance, status quo, and solution for cleaner output."""
    instance.max_staggering_applicable[i] = round(instance.max_staggering_applicable[i], 2)
    instance.deadlines[i] = round(instance.deadlines[i], 2)
    status_quo.start_times[i] = round(status_quo.start_times[i], 2)
    if solution:
        solution.start_times[i] = round(solution.start_times[i], 2)

    for j in range(len(status_quo.congested_schedule[i])):
        status_quo.congested_schedule[i][j] = round(status_quo.congested_schedule[i][j], 2)
        status_quo.delays_on_arcs[i][j] = round(status_quo.delays_on_arcs[i][j], 2)
        if solution:
            solution.congested_schedule[i][j] = round(solution.congested_schedule[i][j], 2)
            solution.delays_on_arcs[i][j] = round(solution.delays_on_arcs[i][j], 2)


def _remove_unnecessary_instance_columns(instance_data_to_save):
    """Remove unnecessary attributes from instance data."""
    columns_to_remove = [
        "instance_params", "capacities_arcs", "release_times_dataset", "arrival_times_dataset",
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

    output_data["instance"].pop("arc_position_in_routes_map", None)


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
