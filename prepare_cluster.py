import csv
import datetime
import itertools
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

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

    print(cluster_setup)
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
        if "GA_" not in model and "GA_" in k:
            continue
        if k == "set_of_experiments":
            continue
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


def get_set_of_experiments_name(preset_name: str, network_name: str, demand_factor_list: list[int],
                                kspwlo_algo_list: list[str],
                                num_alternative_paths_list: list[int], path_similarity_theta_list: list[float],
                                algo_list: list[str], mode_list: list[str], GA_iterations: int, LS_iterations: int,
                                staggering_cap: int, fraction_controlled_list: list[float],
                                goal_list: list[str]) -> str:
    today = datetime.datetime.today()
    # Format the date as ddmmyy
    date_string = today.strftime('%d%m%y')

    name_split: list[str] = network_name.split("_")
    network_abbreviated = name_split[0][:3].upper()
    size = name_split[1]
    name_formatted = network_abbreviated + size

    if len(demand_factor_list) == 1:
        demand_factor_string = "DF" + str(demand_factor_list[0])
    else:
        demand_factor_string = "VARDF"

    if len(kspwlo_algo_list) == 1:
        kspwlo_algo_string = kspwlo_algo_list[0].replace("_", "").upper()
    else:
        kspwlo_algo_string = "VARALGO"

    if len(num_alternative_paths_list) == 1:
        alternative_paths_string = str(num_alternative_paths_list[0]) + "K"
    else:
        alternative_paths_string = "VARK"

    # Path similarity string using THETA as indicator
    if len(path_similarity_theta_list) == 1:
        path_similarity_string = "THETA" + str(path_similarity_theta_list[0])
    else:
        path_similarity_string = "VARTHETA"

    # Algorithm list processing
    if len(algo_list) == 1:
        algo_string = algo_list[0].replace("_", "").upper()
    else:
        algo_string = "VARALGO"

    # Mode list processing
    if len(mode_list) == 1:
        mode_string = mode_list[0].replace("_", "").upper()
    else:
        mode_string = "VARMODES"

    # LS parameterization when using LS as an algorithm
    if "LS" in algo_string:
        LS_iterations = PRESETS[preset_name]["LS_iterations"]
        LS_max_cascade_level = PRESETS[preset_name].get("LS_max_cascade_level", -1)
        LS_ls_frequency = PRESETS[preset_name].get("LS_ls_frequency", 0)
        LS_destroy_percentage = PRESETS[preset_name].get("LS_destroy_percentage", 0)
        LS_improve_with_ls = PRESETS[preset_name].get("LS_improve_with_ls", False)
        LS_min_improvement = PRESETS[preset_name].get("LS_min_improvement", 0.05)

        # Determine whether to append improve_with_ls flag to the experiment name
        improve_with_ls_string = "EndLS" if LS_improve_with_ls else "NoEndLS"

        # Append the LS parameters to the experiment name, including the improvement flag
        ls_params_string = (f"{LS_ls_frequency}LSFreq_"
                            f"{LS_destroy_percentage}DP_{LS_min_improvement}MI_{improve_with_ls_string}")
    else:
        ls_params_string = ""

    # Iterations string
    if algo_string == "VARALGO":
        iterations_string = f"{GA_iterations // 1000}KGAIT_{LS_iterations // 1000}KLSIT"
    elif "GA" in algo_string:
        iterations_string = f"{GA_iterations // 1000}KGAIT"
    elif "LS" in algo_string:
        iterations_string = f"{LS_iterations // 1000}KLSIT"
    else:
        iterations_string = "UNKNOWN"

    # Fraction controlled string
    if len(fraction_controlled_list) == 1:
        fraction_controlled_string = f"{int(fraction_controlled_list[0] * 100)}Contr"
    else:
        fraction_controlled_string = "VARContr"

    # Goal string
    if len(goal_list) == 1:
        goal_string = goal_list[0]
    else:
        goal_string = "VARGoals"

    # Combine everything into the final name string
    final_name = f"{date_string}_{preset_name.upper()}_{name_formatted}_{demand_factor_string}_{staggering_cap}STAGCAP_{kspwlo_algo_string}_" \
                 f"{path_similarity_string}_{alternative_paths_string}_{algo_string}_{mode_string}_" \
                 f"{iterations_string}_{ls_params_string}_{fraction_controlled_string}_{goal_string}"

    print(f"SET OF EXPERIMENT NAME: {final_name}")
    return final_name


PRESETS = {
    "algo_performance": {
        "num_alternative_paths_list": [10],
        "path_similarity_theta_list": [.9],
        "day_list": list(range(1, 32)),
        "staggering_cap": 25,
        "deadline_factor": 100,
        "list_of_slopes_list": [[0.15]],
        "list_of_thresholds": [1],
        "kspwlo_algo_list": ["svp_plus"],
        "fraction_controlled_list": [1],
        "goal_list": ["WELFARE"],
        "algo_list": ["LS"],
        "mode_list": ["STAG", "BAL", "INTEG"],
        "LS_iterations": 1000,
        "LS_max_cascade_level": -1,
        "LS_ls_frequency": 0.2,
        "LS_destroy_percentage": 0.2,
        "LS_improve_with_ls": True,
        "LS_min_improvement": 0.05
    },
    "path_analysis": {
        "num_alternative_paths_list": [2, 5, 10, 20, 30, 50],
        "path_similarity_theta_list": [0, .3, .6, .9, 1],
        "day_list": list(range(1, 32)),
        "staggering_cap": 25,
        "deadline_factor": 100,
        "list_of_slopes_list": [[0.15]],
        "list_of_thresholds": [1],
        "kspwlo_algo_list": ["svp_plus"],
        "fraction_controlled_list": [1],
        "goal_list": ["WELFARE"],
        "algo_list": ["LS"],
        "mode_list": ["BAL"],
        "LS_iterations": 1000,
        "LS_max_cascade_level": -1,
        "LS_ls_frequency": 0.2,
        "LS_destroy_percentage": 0.2,
        "LS_improve_with_ls": True,
        "LS_min_improvement": 0.05
    },

    "fraction_controlled": {
        "num_alternative_paths_list": [10],
        "path_similarity_theta_list": [.9],
        "day_list": [25],
        "staggering_cap": 25,
        "deadline_factor": 100,
        "list_of_slopes_list": [[0.15]],
        "list_of_thresholds": [1],
        "kspwlo_algo_list": ["svp_plus"],
        "fraction_controlled_list": [round(i * 0.1, 1) for i in range(11)],
        "goal_list": ["WELFARE", "SELFISH"],
        "algo_list": ["LS"],
        "mode_list": ["INTEG"],
        "LS_iterations": 1000,
        "LS_max_cascade_level": -1,
        "LS_ls_frequency": 0.2,
        "LS_destroy_percentage": 0.2,
        "LS_improve_with_ls": True,
        "LS_min_improvement": 0.05
    }
}


def main(preset_name: str, network_name: str, demand_factor_list: list[int]):
    """
    Main function to execute the setup and configuration for cluster jobs.
    """
    # Instance parameters

    if preset_name not in PRESETS:
        raise ValueError("preset name not in presets")

    num_alternative_paths_list = PRESETS[preset_name]["num_alternative_paths_list"]
    path_similarity_theta_list = PRESETS[preset_name]["path_similarity_theta_list"]
    day_list = PRESETS[preset_name]["day_list"]
    staggering_cap = PRESETS[preset_name]["staggering_cap"]
    deadline_factor = PRESETS[preset_name]["deadline_factor"]
    list_of_slopes_list = PRESETS[preset_name]["list_of_slopes_list"]
    list_of_thresholds = PRESETS[preset_name]["list_of_thresholds"]
    kspwlo_algo_list = PRESETS[preset_name]["kspwlo_algo_list"]
    fraction_controlled_list = PRESETS[preset_name]["fraction_controlled_list"]

    # Solver parameters
    goal_list = PRESETS[preset_name]["goal_list"]
    algo_list = PRESETS[preset_name]["algo_list"]
    mode_list = PRESETS[preset_name]["mode_list"]
    plot_flag = False
    verbose = False

    # GA parameters
    GA_seed_list = range(1)  # set this to range(1) if not using GA
    GA_population_size_list = [100]
    GA_iterations = 5000
    GA_penalization = 10
    GA_it_pen = 1000
    GA_crossover_mode_list = ["UN"]  # 2P, UN, 1P
    GA_parents_selection_mode_list = ["2ARY"]  # kARY, #FIT
    GA_start_times_distribution_list = ["NOR"]  # NOR #UN
    GA_offspring_operator = "MUT"  # MUT #EDU #None

    # LS parameterization
    LS_iterations = PRESETS[preset_name]["LS_iterations"]
    LS_max_cascade_level = PRESETS[preset_name]["LS_max_cascade_level"]
    LS_ls_frequency = PRESETS[preset_name]["LS_ls_frequency"]
    LS_destroy_percentage = PRESETS[preset_name]["LS_destroy_percentage"]
    LS_improve_with_ls = PRESETS[preset_name]["LS_improve_with_ls"]
    LS_min_improvement = PRESETS[preset_name]["LS_min_improvement"]

    set_of_experiments = get_set_of_experiments_name(preset_name, network_name, demand_factor_list, kspwlo_algo_list,
                                                     num_alternative_paths_list, path_similarity_theta_list,
                                                     algo_list, mode_list, GA_iterations, LS_iterations, staggering_cap,
                                                     fraction_controlled_list, goal_list)

    # Cluster parameters
    job_title = set_of_experiments
    job_priority = "NORMAL"  # NORMAL, URGENT
    if network_name == "manhattan_5":
        minutes_per_run = 30
        memory_per_cpu = "2G"
    elif network_name == "manhattan_10":
        minutes_per_run = 60
        memory_per_cpu = "5G"
    else:
        minutes_per_run = 500
        memory_per_cpu = "10G"
    node_type = "ANY"
    cpu_per_run = 1

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
        for num_alternative_paths in num_alternative_paths_list:
            for demand_factor in demand_factor_list:
                for list_of_slopes in list_of_slopes_list:
                    for path_similarity_theta in path_similarity_theta_list:
                        for kspwlo_algo in kspwlo_algo_list:
                            for fraction_controlled in fraction_controlled_list:
                                # Create a dictionary of parameters for the current configuration
                                instance_params_dict = {
                                    "network_name": network_name,
                                    "day": day,
                                    "number_trips": 0,
                                    "staggering_cap": staggering_cap,
                                    "deadline_factor": deadline_factor,
                                    "list_of_slopes": list_of_slopes,
                                    "list_of_thresholds": list_of_thresholds,
                                    "num_alternative_paths": num_alternative_paths,
                                    "path_similarity_theta": path_similarity_theta,
                                    "kspwlo_algo": kspwlo_algo,
                                    "demand_factor": demand_factor,
                                    "fraction_controlled": fraction_controlled
                                }
                                instance_params_name = get_csv_data_name(instance_params_dict)
                                write_instance_parameters_csv(instance_params_dict, instance_params_name,
                                                              mode="instance")
                                instance_params_names_list.append(instance_params_name)

    # Define solver parameters for the simulation
    solver_params_list = []
    for algo in algo_list:
        for mode in mode_list:
            for seed in GA_seed_list:
                for GA_population_size in GA_population_size_list:
                    for GA_parents_selection_mode in GA_parents_selection_mode_list:
                        for GA_crossover_mode in GA_crossover_mode_list:
                            for GA_start_times_distribution in GA_start_times_distribution_list:
                                for goal in goal_list:
                                    solver_params_dict = {
                                        "algo": algo,
                                        "mode": mode,
                                        "GA_seed": seed,
                                        "GA_population_size": GA_population_size,
                                        "GA_iterations": GA_iterations,
                                        "GA_penalization": GA_penalization,
                                        "GA_it_pen": GA_it_pen,
                                        "GA_crossover_mode": GA_crossover_mode,  # 2P, UN
                                        "GA_parents_selection_mode": GA_parents_selection_mode,  # BIN, #FIT
                                        "GA_start_times_distribution": GA_start_times_distribution,  # NOR #UN
                                        "GA_offspring_operator": GA_offspring_operator,
                                        "verbose": verbose,
                                        "plot_flag": plot_flag,
                                        "LS_iterations": LS_iterations,
                                        "goal": goal,
                                        "LS_max_cascade_level": LS_max_cascade_level,
                                        "LS_ls_frequency": LS_ls_frequency,
                                        "LS_destroy_percentage": LS_destroy_percentage,
                                        "LS_improve_with_ls": LS_improve_with_ls,
                                        "LS_min_improvement": LS_min_improvement
                                    }

                                    # Generate the solver parameters filename
                                    solver_params_name = get_csv_data_name(solver_params_dict)
                                    write_instance_parameters_csv(solver_params_dict, solver_params_name, mode="solver")
                                    solver_params_list.append(solver_params_name)

    # Execution
    write_run_list(instance_params_names_list, solver_params_list, set_of_experiments, cluster_setup.job_title)
    create_cluster_configuration(cluster_setup)


if __name__ == "__main__":
    main(preset_name="fraction_controlled", network_name="manhattan_20", demand_factor_list=[10])
