import csv
import itertools
import os
import pprint
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from tabulate import tabulate
import datetime
from PRESETS import PRESETS

# Define paths relative to the current script location
path_to_data = Path(__file__).parent / "data"
path_to_instructions = path_to_data / "instructions"
path_to_instance_params = path_to_instructions / "instance_parameters"
path_to_solver_params = path_to_instructions / "solver_parameters"
os.makedirs(path_to_instance_params, exist_ok=True)
os.makedirs(path_to_solver_params, exist_ok=True)


@dataclass
class ClusterSetup:
    job_title: str
    memory_per_cpu: str  # e.g., "12G"
    minutes_per_run: int
    job_priority: str  # "urgent" or "normal"
    node_type: str  # "ANY", "CPU_ONLY", "GPU_ONLY"
    cpu_per_run: int


def write_run_list(instance_params_names: list[str],
                   solver_params_names: list[str],
                   sets_of_experiments: str,
                   job_title: str) -> None:
    """
    Creates run list, setup CSV files, and a job summary Excel sheet for cluster execution.
    """
    run_list_rows = []
    for i, full_params in enumerate(itertools.product(instance_params_names, solver_params_names), start=1):
        exp_name = f"{job_title}_{i}"
        instance_name = full_params[0]
        solver_params_name = full_params[1]
        run_list_row = [exp_name, instance_name, solver_params_name, sets_of_experiments]
        run_list_rows.append(run_list_row)
    print("Number of experiments: ", len(run_list_rows))

    # Write the run list to a CSV file
    with open('run_list.csv', 'w', newline='\n', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(run_list_rows)


def remove_old_setups():
    """
    Removes old setup files from the setups directory.
    """
    folder = 'setups'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def create_cluster_configuration(cluster_setup: ClusterSetup) -> None:
    """Creates a cluster configuration bash script with the given setup."""
    # Assuming cluster_setup is your dataclass instance
    print("=" * 50)
    print("CLUSTER SETUP".center(50))
    print("=" * 50)
    pprint.pprint(asdict(cluster_setup))
    with open("my_cluster_configuration.sh", "w") as file:
        file.writelines([
            "#!/bin/bash\n",
            f"export MY_JOB_NAME='{cluster_setup.job_title}'\n",
            f"export MY_MEMORY_PER_CPU='{cluster_setup.memory_per_cpu}'\n",
            f"export MY_MINUTES_PER_RUN={cluster_setup.minutes_per_run}\n",
            f"export MY_PRIORITY={cluster_setup.job_priority}\n",
            f"export MY_NODE_TYPE='{cluster_setup.node_type}'\n",
            f"export MY_CPU_PER_RUN={cluster_setup.cpu_per_run}\n"
        ])


def get_csv_data_name(params_dict: dict) -> str:
    """
    Generate a CSV filename from the values in the input data dictionary.
    Colons in time strings are replaced with underscores to avoid file path issues.
    """
    input_data_name = ""
    model = params_dict.get("model", "")
    for k, value in params_dict.items():
        if k == "set_of_experiments":
            continue
        if k in ["list_of_thresholds", "list_of_slopes"]:
            if isinstance(value, list) and len(value) > 1:
                # Format value for lists to enclose in brackets and replace comma and whitespace with underscore
                value = f"[{'_'.join(map(str, value))}]"
            else:
                value = str(value)
        input_data_name += f"{str(value)}_"
    input_data_name = input_data_name[:-1].replace(":", "_")  # Remove trailing underscore and replace colons
    return f"{input_data_name}.csv"


def write_instance_parameters_csv(input_data_dict, input_data_name, mode: str):
    if mode == "solver":
        path_to_params = path_to_solver_params
    elif mode == "instance":
        path_to_params = path_to_instance_params
    else:
        raise ValueError("undefined case")

    # Write the configuration to a CSV file
    with open(path_to_params / input_data_name, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=input_data_dict.keys())
        writer.writeheader()  # Write the column names as the header
        writer.writerow(input_data_dict)  # Write the data row


def format_list_as_range(lst):
    """Formats a list of integers into a compact range format."""
    if not lst:
        return "[]"
    ranges = []
    start = lst[0]
    for i in range(1, len(lst)):
        if lst[i] != lst[i - 1] + 1:
            end = lst[i - 1]
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = lst[i]
    ranges.append(f"{start}-{lst[-1]}" if start != lst[-1] else str(start))
    return ", ".join(ranges)


def pretty_print_experiment_parameters(
        preset_parameters: dict, network_name: str, number_of_trips: int, add_shortcuts: bool):
    # Start with the explicitly passed arguments
    parameters = [
        ("Network Name", network_name),
        ("Number of Trips", number_of_trips),
        ("Add Shortcuts", "Yes" if add_shortcuts else "No")
    ]

    # Add the parameters from the preset dictionary
    for key, value in preset_parameters.items():
        # Special handling for the day list
        if key == "day_list" and isinstance(value, list):
            value = format_list_as_range(value)
        parameters.append((key.replace("_", " ").title(), value))

    # Print the table using tabulate
    print(tabulate(parameters, headers=["Parameter", "Value"], tablefmt="simple"))


def get_set_of_experiments_name(preset_name: str, custom_note: str = "") -> str:
    """
    Generate a simple experiment name with timestamp and preset name.
    Format: DAYMONTH_HOURMIN_PRESETNAME_{OPTIONAL_NOTE}
    """
    timestamp = datetime.datetime.now().strftime("%d%m_%H%M")
    parts = [timestamp, preset_name.upper()]

    if custom_note:
        parts.append(custom_note.upper())

    return "_".join(parts)


def main(preset_name: str, add_shortcuts: bool):
    """
    Main function to execute the setup and configuration for cluster jobs.
    """
    # Sanity checks
    if preset_name not in PRESETS:
        raise ValueError("preset name not in presets")

    # Instance parameters
    network_name = PRESETS[preset_name]["network_name"]
    number_of_trips = PRESETS[preset_name]["number_of_trips"]
    day_list = PRESETS[preset_name]["day_list"]
    max_flow_allowed_list = PRESETS[preset_name]["max_flow_allowed_list"]
    seed_list = PRESETS[preset_name]["seed_list"]
    list_of_slopes_list = PRESETS[preset_name]["list_of_slopes_list"]
    list_of_thresholds_list = PRESETS[preset_name]["list_of_thresholds_list"]
    staggering_cap_list = PRESETS[preset_name]["staggering_cap_list"]
    deadline_factor = PRESETS[preset_name]["deadline_factor"]
    max_length_shortcut = PRESETS[preset_name]["max_length_shortcut"]

    # Solver parameters
    algo_mode_list = PRESETS[preset_name]["algo_mode_list"]
    epoch_size_list = [60 if x == "OFFLINE" else 6 for x in algo_mode_list]
    optimize = PRESETS[preset_name]["optimize"]
    warm_start = PRESETS[preset_name]["warm_start"]
    improve_warm_start_list = PRESETS[preset_name]["improve_warm_start_list"]
    simplify = PRESETS[preset_name]["simplify"]
    verbose_model = PRESETS[preset_name]["verbose_model"]

    # Cluster parameters
    set_of_experiments = get_set_of_experiments_name(preset_name, "COLLECTING_INSTANCES")

    job_title = set_of_experiments
    job_priority = PRESETS[preset_name]["job_priority"]  # NORMAL, URGENT
    cpu_per_run = PRESETS[preset_name]["cpu_per_run"]
    node_type = PRESETS[preset_name]["node_type"]
    minutes_per_run = PRESETS[preset_name]["minutes_per_run"]
    memory_per_cpu = PRESETS[preset_name]["memory_per_cpu"]

    pretty_print_experiment_parameters(PRESETS[preset_name], network_name, number_of_trips,
                                       add_shortcuts)

    # cluster_setup
    cluster_setup = ClusterSetup(
        job_title=job_title,
        job_priority=job_priority,  # "URGENT" or "NORMAL"
        minutes_per_run=minutes_per_run,  # minutes
        memory_per_cpu=memory_per_cpu,
        node_type=node_type,
        cpu_per_run=cpu_per_run
    )

    instance_params_names_list = []
    for day in day_list:
        for seed in seed_list:
            for staggering_cap in staggering_cap_list:
                for max_flow_allowed in max_flow_allowed_list:
                    for pwl_id in range(len(list_of_slopes_list)):
                        # Create a dictionary of parameters for the current configuration
                        instance_params_dict = {
                            "network_name": network_name,
                            "day": day,
                            "number_of_trips": number_of_trips,
                            "seed": seed,
                            "max_flow_allowed": max_flow_allowed,
                            "add_shortcuts": add_shortcuts,
                            "max_length_shortcut": max_length_shortcut,
                            "list_of_slopes": list_of_slopes_list[pwl_id],
                            "list_of_thresholds": list_of_thresholds_list[pwl_id],
                            "staggering_cap": staggering_cap,
                            "deadline_factor": deadline_factor
                        }
                        instance_params_name = get_csv_data_name(instance_params_dict)
                        write_instance_parameters_csv(instance_params_dict, instance_params_name, mode="instance")
                        instance_params_names_list.append(instance_params_name)

    # Define solver parameters for the simulation
    solver_params_list = []
    for epoch_size in epoch_size_list:
        for improve_warm_start in improve_warm_start_list:
            if "mini" in preset_name:
                epoch_time_limit = 60 if epoch_size == 60 else 10
            else:
                epoch_time_limit = 3600 if epoch_size == 60 else 360
            solver_params_dict = {
                "epoch_time_limit": epoch_time_limit,
                "epoch_size": epoch_size,
                "optimize": optimize,
                "warm_start": warm_start,
                "improve_warm_start": improve_warm_start,
                "local_search_callback": improve_warm_start,  # on purpose, same as improve warm start
                "simplify": simplify,
                "verbose_model": verbose_model
            }

            # Generate the solver parameters filename
            solver_params_name = get_csv_data_name(solver_params_dict)
            write_instance_parameters_csv(solver_params_dict, solver_params_name, mode="solver")
            solver_params_list.append(solver_params_name)

    # Execution
    write_run_list(instance_params_names_list, solver_params_list, set_of_experiments, cluster_setup.job_title)
    create_cluster_configuration(cluster_setup)


if __name__ == "__main__":
    main(preset_name="check_instances", add_shortcuts=True)

# PRESETS NAMES
# algo_performance_paper
# staggering_analysis_paper
# var_pwl_paper
# no_ls_comparison_paper
