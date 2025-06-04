import ast
import csv
import dataclasses
import os
import sys
from pathlib import Path
from tabulate import tabulate  # Import the tabulate library
import datetime
from typing import Optional

# Global configuration parameters
SAVE_CPP = True  # Saves files to run catch2 tests in cpp_module
ACTIVATE_ASSERTIONS = False
FIX_MODEL = False
USE_GUROBI_INDICATORS = False
SPEED_KPH = 20  # kph
TOLERANCE = 1e-6
MIN_SET_CAPACITY = 1.01
CONSTR_TOLERANCE = 1e-3
GUROBI_OPTIMALITY_GAP = 0.01
dateExperiment = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
os.environ['USE_PYGEOS'] = '0'  # Suppress warning from Shapely library


@dataclasses.dataclass
class InstanceParameters:
    network_name: str
    add_shortcuts: bool
    max_length_shortcut: int  # [meters]
    day: int
    number_of_trips: int
    seed: int
    max_flow_allowed: float
    list_of_slopes: list[float]
    list_of_thresholds: list[float]
    staggering_cap: float
    deadline_factor: float

    def __post_init__(self):
        self.validate_inputs()
        self.path_to_G = Path(
            __file__).parent.parent / f"data/{self.network_name}/{self.get_shortcuts_string()}SHORTCUTS/network.json"
        self.path_to_routes = self.path_to_G.parent / f"{self.get_day_string()}{self.get_number_trips_string()}/routes.json"
        self.path_to_instance = self.path_to_routes.parent / f"SEED{self.seed}_MFA{self.max_flow_allowed}_STAG{self.staggering_cap}_D{self.deadline_factor}_VDF{self.list_of_slopes}{self.list_of_thresholds}/instance.json"
        os.makedirs(self.path_to_instance.parent, exist_ok=True)

    def get_shortcuts_string(self):
        if self.add_shortcuts:
            return f"WITH_{self.max_length_shortcut}M_"
        else:
            return "NO_"

    def validate_inputs(self):
        if "manhattan_" not in self.network_name:
            raise ValueError("Network name must be manhattan_X, with X being percentage of nodes to retain.")
        if self.day not in range(1, 32):
            raise ValueError("Day must be between 1 and 31.")
        if self.deadline_factor < 0 or self.deadline_factor > 100:
            raise ValueError("Deadline factor must be between 0 and 100.")

    def get_number_trips_string(self) -> str:
        return f"T{self.number_of_trips}"

    def get_day_string(self) -> str:
        return f"DAY{self.day}_"


@dataclasses.dataclass
class SolverParameters:
    epoch_time_limit: int
    epoch_size: int
    optimize: bool
    warm_start: bool
    improve_warm_start: bool
    local_search_callback: bool
    simplify: bool
    instance_parameters: InstanceParameters
    set_of_experiments: Optional[str]
    verbose_model: bool
    start_algorithm_clock: float = 0

    def __post_init__(self):
        self.path_to_results = self.instance_parameters.path_to_instance.parent / (f"{self.get_string_mode()}/"
                                                                                   f"OPT{'YES' if self.optimize else 'NO'}_"
                                                                                   f"WARM{'YES' if self.warm_start else 'NO'}_"
                                                                                   f"IWARM{'YES' if self.improve_warm_start else 'NO'}_"
                                                                                   f"CBLS{'YES' if self.local_search_callback else 'NO'}_"
                                                                                   f"SPLFY{'YES' if self.simplify else 'NO'}")

    def get_string_mode(self) -> str:
        if self.epoch_size == 60:
            return "OFFLINE"
        else:
            return "ONLINE"


def print_parameters(instance_parameters, solver_parameters):
    # Get current date and time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("-" * 50)
    print("INFO EXPERIMENT".center(50))
    print("=" * 50)
    print(f"Experiment Date and Time: {current_time}")
    print("-" * 50)

    # Function to prepare data for printing by removing paths and converting to tabulate format
    def prepare_data_for_printing(parameters, mode: str, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = []
        data_to_print = {k: v for k, v in vars(parameters).items() if 'path' not in k and k not in exclude_keys}
        return tabulate(list(data_to_print.items()), headers=[f'{mode} Parameters', 'Value'], tablefmt='simple')

    # Print instance parameters
    print(prepare_data_for_printing(instance_parameters, "Instance"))
    print("-" * 50)

    # Print solver parameters, ensuring no overlap with instance parameter keys
    print(prepare_data_for_printing(solver_parameters, "Solver", exclude_keys=["instance_parameters"]))
    print("-" * 50)

    print("=" * 100)
    print("START PROCEDURE".center(100))
    print("=" * 100)


def generate_input_data_from_script() -> tuple[InstanceParameters, SolverParameters]:
    instance_params = InstanceParameters(
        day=5,
        number_of_trips=500,
        seed=0,
        network_name="manhattan_7",
        max_flow_allowed=20,
        add_shortcuts=True,
        max_length_shortcut=500,
        list_of_slopes=[0.15],
        list_of_thresholds=[1],
        deadline_factor=100,
        staggering_cap=25)

    solver_params = SolverParameters(epoch_size=60, epoch_time_limit=1,
                                     optimize=True, warm_start=True, improve_warm_start=True,
                                     local_search_callback=True,
                                     simplify=True, instance_parameters=instance_params, set_of_experiments="local",
                                     verbose_model=True)
    return instance_params, solver_params


def read_params(mode: str, params_name: str) -> dict:
    """Import dict with instance params from file"""
    path_to_instructions = Path(__file__).parent.parent / "data" / "instructions"
    if mode not in ["instance", "solver"]:
        raise ValueError("mode must be instance or solver")
    path_to_params = path_to_instructions / f"{mode}_parameters/{params_name}"
    with open(path_to_params, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        keys = next(csv_reader)
        values = next(csv_reader)
    params_dict = dict(zip(keys, values))
    return params_dict


def format_bool(arg_string_bool: str):
    if arg_string_bool == "True":
        return True
    else:
        return False


def format_set_of_experiments_string(s: str):
    """Set of experiments string might be None"""
    if s == "None":
        return None
    else:
        return s


def get_input_from_dicts(instance_params_dict: dict, solver_params_dict: dict) -> \
        (InstanceParameters, SolverParameters):
    """Called when using console args - transforms dicts in params"""
    list_of_thresholds = instance_params_dict["list_of_thresholds"]
    list_of_slopes = instance_params_dict["list_of_slopes"]

    if isinstance(list_of_thresholds, str):
        # Use ast.literal_eval to safely evaluate the string as a Python expression
        list_of_thresholds = ast.literal_eval(list_of_thresholds)
        list_of_slopes = ast.literal_eval(list_of_slopes)

    instance_params = InstanceParameters(
        network_name=instance_params_dict["network_name"],
        day=int(instance_params_dict["day"]),
        list_of_slopes=list_of_slopes,
        list_of_thresholds=list_of_thresholds,
        staggering_cap=float(instance_params_dict["staggering_cap"]),
        deadline_factor=float(instance_params_dict["deadline_factor"]),
        seed=int(instance_params_dict["seed"]),
        max_flow_allowed=float(instance_params_dict["max_flow_allowed"]),
        number_of_trips=int(instance_params_dict["number_of_trips"]),
        add_shortcuts=format_bool(instance_params_dict["add_shortcuts"]),
        max_length_shortcut=int(instance_params_dict["max_length_shortcut"])
    )

    solver_params = SolverParameters(
        set_of_experiments=format_set_of_experiments_string(sys.argv[3]),
        instance_parameters=instance_params,
        epoch_size=int(solver_params_dict["epoch_size"]),
        optimize=format_bool(solver_params_dict["optimize"]),
        warm_start=format_bool(solver_params_dict["warm_start"]),
        improve_warm_start=format_bool(solver_params_dict["improve_warm_start"]),
        local_search_callback=format_bool(solver_params_dict["local_search_callback"]),
        epoch_time_limit=int(solver_params_dict["epoch_time_limit"]),
        verbose_model=format_bool(solver_params_dict["verbose_model"]),
        simplify=format_bool(solver_params_dict["simplify"])
    )

    return instance_params, solver_params


def load_input_data_from_file() -> tuple[InstanceParameters, SolverParameters]:
    instance_params_name = sys.argv[1]
    solver_params_name = sys.argv[2]

    instance_params_dict = read_params("instance", instance_params_name)
    solver_params_dict = read_params("solver", solver_params_name)
    instance_params, solver_params = get_input_from_dicts(instance_params_dict, solver_params_dict)
    return instance_params, solver_params


def get_input_data(input_source: str) -> tuple[InstanceParameters, SolverParameters]:
    if input_source == "script":
        instance_params, solver_params = generate_input_data_from_script()
    elif input_source == "console":
        instance_params, solver_params = load_input_data_from_file()
    else:
        raise ValueError("Invalid input source specified.")
    print_parameters(instance_params, solver_params)
    return instance_params, solver_params
