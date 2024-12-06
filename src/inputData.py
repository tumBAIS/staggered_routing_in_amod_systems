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
class InputData:
    network_name: str
    day: int
    number_of_trips: float
    seed: int
    speed: int
    max_flow_allowed: float
    algorithm_time_limit: int
    epoch_time_limit: int
    add_shortcuts: bool
    list_of_slopes: list[float]
    list_of_thresholds: list[float]
    staggering_cap: float
    deadline_factor: float
    optimize: bool
    epoch_size: int
    warm_start: bool
    improve_warm_start: bool
    call_local_search: bool
    staggering_applicable_method: str

    def __post_init__(self):
        self.validate_inputs()
        self.path_to_G = Path(__file__).parent.parent / f"data/{self.network_name}/network.json"
        self.path_to_routes = self.path_to_G.parent / f"{self.get_day_string()}{self.get_number_trips_string()}/routes.json"
        self.path_to_instance = self.path_to_routes.parent / f"S{self.staggering_cap}_D{self.deadline_factor}_VDF{self.list_of_slopes}{self.list_of_thresholds}/instance.json"
        self.path_to_results = self.path_to_instance.parent / "RESULTS"
        os.makedirs(self.path_to_instance.parent, exist_ok=True)
        self.demand_factor = 1  # Placeholder for actual implementation

    def validate_inputs(self):
        if self.day not in range(1, 32):
            raise ValueError("Day must be between 1 and 31.")
        if self.staggering_applicable_method not in ["fixed", "proportional"]:
            raise ValueError("Specify correct staggering method (fixed or proportional).")
        if self.deadline_factor < 0 or self.deadline_factor > 100:
            raise ValueError("Deadline factor must be between 0 and 100.")

    def get_number_trips_string(self) -> str:
        return f"T{self.number_of_trips}"

    def get_day_string(self) -> str:
        return f"DAY{self.day}_" if "manhattan" in self.network_name else ""


def print_input_data(input_data: InputData):
    # Get current date and time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("-" * 50)
    print("INFO EXPERIMENT".center(50))
    print("=" * 50)

    # Print the date and time the experiment is being run
    print(f"Experiment Date and Time: {current_time}")
    print("-" * 50)

    # Filter and prepare data for printing, exclude path attributes
    data_to_print = {k: v for k, v in vars(input_data).items() if not 'path' in k}

    # Convert dictionary to a list of tuples for tabulate
    data_items = list(data_to_print.items())
    # Create a tabular format, specifying the headers
    table = tabulate(data_items, headers=['Parameter', 'Value'], tablefmt='simple')

    # Print the formatted table
    print(table)

    print("-" * 50)
    print("START PROCEDURE".center(50))
    print("=" * 50)


def get_input_data(input_source: str) -> InputData:
    if input_source == "script":
        input_data = generate_input_data_from_script()
    elif input_source == "console":
        input_data = load_input_data_from_file()
    else:
        raise ValueError("Invalid input source specified.")
    print_input_data(input_data)
    return input_data


def generate_input_data_from_script() -> InputData:
    return InputData(
        day=1, number_of_trips=100, epoch_size=60, seed=0, network_name="manhattan_10",
        speed=20, max_flow_allowed=100, add_shortcuts=False,
        list_of_slopes=[0.05], list_of_thresholds=[1],
        staggering_applicable_method="proportional", deadline_factor=100, staggering_cap=10,
        optimize=True, algorithm_time_limit=10, epoch_time_limit=10, warm_start=True,
        improve_warm_start=True, call_local_search=True)


def load_input_data_from_file() -> InputData:
    print(f"Experiment title: {str(sys.argv[1])}")
    with open(f"setups/{sys.argv[1]}", "rb") as infile:
        return pickle.load(infile)
