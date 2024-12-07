import dataclasses
import os
import pickle
import sys
from pathlib import Path
from tabulate import tabulate  # Import the tabulate library
import datetime

# Global configuration parameters
ACTIVATE_ASSERTIONS = False
FIX_MODEL = False
SAVE_CPP_INSTANCE = False
USE_GUROBI_INDICATORS = False
TOLERANCE = 1e-6
MIN_SET_CAPACITY = 1.01
CONSTR_TOLERANCE = 1e-3
GUROBI_OPTIMALITY_GAP = 0.01
dateExperiment = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
os.environ['USE_PYGEOS'] = '0'  # Suppress warning from Shapely library


@dataclasses.dataclass
class InstanceParameters:
    network_name: str
    day: int
    number_of_trips: float
    seed: int
    speed: int
    max_flow_allowed: float
    add_shortcuts: bool
    list_of_slopes: list[float]
    list_of_thresholds: list[float]
    staggering_cap: float
    deadline_factor: float

    def __post_init__(self):
        self.validate_inputs()
        self.path_to_G = Path(
            __file__).parent.parent / f"data/{self.network_name}/{self.get_shortcuts_string()}SHORTCUTS/network.json"
        self.path_to_routes = self.path_to_G.parent / f"{self.get_day_string()}{self.get_number_trips_string()}/routes.json"
        self.path_to_instance = self.path_to_routes.parent / f"S{self.staggering_cap}_D{self.deadline_factor}_VDF{self.list_of_slopes}{self.list_of_thresholds}/instance.json"
        os.makedirs(self.path_to_instance.parent, exist_ok=True)
        self.demand_factor = 1  # Placeholder for actual implementation

    def get_shortcuts_string(self):
        if self.add_shortcuts:
            return "WITH_"
        else:
            return "WITHOUT_"

    def validate_inputs(self):
        if self.day not in range(1, 32):
            raise ValueError("Day must be between 1 and 31.")
        if self.deadline_factor < 0 or self.deadline_factor > 100:
            raise ValueError("Deadline factor must be between 0 and 100.")

    def get_number_trips_string(self) -> str:
        return f"T{self.number_of_trips}"

    def get_day_string(self) -> str:
        return f"DAY{self.day}_" if "manhattan" in self.network_name else ""


@dataclasses.dataclass
class SolverParameters:
    algorithm_time_limit: int
    epoch_time_limit: int
    epoch_size: int
    optimize: bool
    warm_start: bool
    improve_warm_start: bool
    local_search_callback: bool
    instance_parameters: InstanceParameters

    def __post_init__(self):
        self.path_to_results = self.instance_parameters.path_to_instance.parent / "RESULTS"


def print_parameters(instance_parameters, solver_parameters):
    # Get current date and time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("-" * 50)
    print("INFO EXPERIMENT".center(50))
    print("=" * 50)
    print(f"Experiment Date and Time: {current_time}")
    print("-" * 50)

    # Function to prepare data for printing by removing paths and converting to tabulate format
    def prepare_data_for_printing(parameters, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = []
        data_to_print = {k: v for k, v in vars(parameters).items() if 'path' not in k and k not in exclude_keys}
        return tabulate(list(data_to_print.items()), headers=['Parameter', 'Value'], tablefmt='simple')

    # Print instance parameters
    print("Instance Parameters:")
    print(prepare_data_for_printing(instance_parameters))
    print("-" * 50)

    # Print solver parameters, ensuring no overlap with instance parameter keys
    print("Solver Parameters:")
    print(prepare_data_for_printing(solver_parameters, exclude_keys=["instance_parameters"]))
    print("-" * 50)

    print("START PROCEDURE".center(50))
    print("=" * 50)


def generate_input_data_from_script() -> tuple[InstanceParameters, SolverParameters]:
    instance_params = InstanceParameters(
        day=1, number_of_trips=100, seed=0, network_name="manhattan_10",
        speed=20, max_flow_allowed=100, add_shortcuts=False,
        list_of_slopes=[0.15], list_of_thresholds=[1], deadline_factor=100, staggering_cap=10)

    solver_params = SolverParameters(epoch_size=60, optimize=True, algorithm_time_limit=10, epoch_time_limit=10,
                                     warm_start=True, improve_warm_start=True, local_search_callback=True,
                                     instance_parameters=instance_params)
    return instance_params, solver_params


def load_input_data_from_file() -> tuple[InstanceParameters, SolverParameters]:
    # TODO: correctly implement
    print(f"Experiment title: {str(sys.argv[1])}")
    with open(f"setups/{sys.argv[1]}", "rb") as infile:
        return pickle.load(infile)


def get_input_data(input_source: str) -> tuple[InstanceParameters, SolverParameters]:
    if input_source == "script":
        instance_params, solver_params = generate_input_data_from_script()
    elif input_source == "console":
        instance_params, solver_params = load_input_data_from_file()
    else:
        raise ValueError("Invalid input source specified.")
    print_parameters(instance_params, solver_params)
    return instance_params, solver_params
