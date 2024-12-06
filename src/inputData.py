import dataclasses
import datetime
import os
import pickle
import sys
from pathlib import Path

"set paths"
pathToRepository = os.path.join(os.path.dirname(__file__), "..")
pathToSrc = os.path.join(os.path.dirname(__file__), "../src")
sys.path.append(pathToRepository)
sys.path.append(pathToSrc)
os.chdir(pathToRepository)
C_MAKE_CONFIGURATION = "relwithdebinfo"
sys.path.append(f'./cpp_module/cmake-build-{C_MAKE_CONFIGURATION}')

"Global parameters"
ACTIVATE_ASSERTIONS = False
FIX_MODEL = False
SAVE_CPP_INSTANCE = False
USE_GUROBI_INDICATORS = False
TOLERANCE = 1e-6
MIN_SET_CAPACITY = 1.01
CONSTR_TOLERANCE = 1 * 1e-3
GUROBI_OPTIMALITY_GAP = 0.01
dateExperiment = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
# https://gis.stackexchange.com/questions/397482/what-does-this-warning-mean-for-shapely-python
os.environ['USE_PYGEOS'] = '0'  # to suppress shapely warning


# Suppress specific FutureWarning from geopandas


@dataclasses.dataclass
class InputData:
    t_min: int  # Time windows departures [minutes]
    network_name: str  # Area of manhattan to consider
    type_of_instance: str  # If True, samples numberRides, otherwise gets all trips occured in the area specified
    day: int  # Day for instanceModule selection
    numberRides: float  # Number of rides to consider
    seed: int  # Seed used to sample data
    speed: int  # Speed of the vehicles
    maxFlowAllowed: float  # Maximum flow allowed
    algorithmTimeLimit: int  # Total time limit for optimization
    epochTimeLimit: int  # Total time limit for solving an epoch (in seconds)
    addShortcuts: bool  # Whether to add shortcuts in the network
    list_of_slopes: list[float]  # Ordered list of slopes of the pwl latency
    list_of_thresholds: list[float]  # Ordered list of thresholds of the pwl latency
    staggering_cap: float  # Cap minutes of maximum staggering
    deadline_factor: float  # Comprised between 0 and 100, delta to extend deadline
    optimize: bool  # If True, construct and run model
    epochSize: int  # size of each epoch in minutes
    warmStart: bool  # feed warm start solution to model
    improveWarmStart: bool  # Run local search on status quo
    callLocalSearch: bool  # use local search in callback
    staggeringApplicableMethod: str  # method to assign staggering to trips: fixed or proportional to trip length

    def __post_init__(self):
        if self.type_of_instance not in ["synthetic", "all_true_rides", "sampled_true_rides"]:
            return RuntimeError("type of instance can be: synthetic, all_true_rides, sampled_true_rides")
        if self.day not in range(1, 32):
            raise RuntimeError("day must be between 1 and 31")
        if self.staggeringApplicableMethod not in ["fixed", "proportional"]:
            raise RuntimeError("specif correct deadline method (fixed or proportional)")
        if self.deadline_factor < 0 or self.deadline_factor > 100:
            raise RuntimeError("deadline factor must be comprised between 0 and 100")

        self.demand_factor = 1  # TODO: create proper parameter

        self.path_to_G = Path(__file__).parent.parent / f"data/{self.network_name}/network.json"
        self.path_to_routes = self.path_to_G.parent / f"{self.get_day_string()}{self.get_number_trips_string()}/routes.json"
        self.path_to_instance = self.path_to_routes.parent / f"S{self.staggering_cap}_D{self.deadline_factor}_" \
                                                             f"VDF{self.list_of_slopes}{self.list_of_thresholds}/instance.json"
        self.path_to_results = self.path_to_instance.parent / f"RESULTS"
        os.makedirs(self.path_to_instance.parent, exist_ok=True)

    def get_number_trips_string(self) -> str:
        return f"T{self.numberRides}"

    def get_day_string(self) -> str:
        if "manhattan" in self.network_name:
            return f"DAY{self.day}_"
        else:
            return ""


def printInputData(inputData):
    print("#" * 20)
    print("# INFO EXPERIMENT #")
    print("#" * 20)

    infoToPrint = vars(inputData)
    quarterOfPararms = round(0.25 * len(infoToPrint))

    # Get the current date and time
    now = datetime.datetime.now()
    # Format the time and day
    time_and_day = now.strftime("%d/%m/%Y %H:%M:%S %A")

    # Print the time and day
    print("Current time and day: ", time_and_day)

    print({k: v for i, (k, v) in enumerate(infoToPrint.items()) if i < quarterOfPararms})
    print({k: v for i, (k, v) in enumerate(infoToPrint.items()) if quarterOfPararms <= i < 2 * quarterOfPararms})
    print({k: v for i, (k, v) in enumerate(infoToPrint.items()) if 2 * quarterOfPararms <= i < 3 * quarterOfPararms})
    print({k: v for i, (k, v) in enumerate(infoToPrint.items()) if i > 3 * quarterOfPararms})

    print("#" * 20)
    print("# START PROCEDURE #")
    print("#" * 20)


def get_input_data(input: str) -> InputData:
    if input == "script":
        inputData = InputData(
            # instanceModule selection
            day=1, numberRides=100, t_min=0, epochSize=60, seed=0, network_name="manhattan_10",
            type_of_instance="synthetic",
            # network parameters
            speed=20, maxFlowAllowed=100, addShortcuts=False,
            # vdf parameters
            list_of_slopes=[0.05], list_of_thresholds=[1],
            # other parameters
            staggeringApplicableMethod="proportional", deadline_factor=100, staggering_cap=10,
            # algorithm parameters
            optimize=True, algorithmTimeLimit=10, epochTimeLimit=10, warmStart=True,
            improveWarmStart=True, callLocalSearch=True)
    elif input == "console":
        print(f"Experiment title: {str(sys.argv[1])}")
        with open(f"setups/{sys.argv[1]}", "rb") as infile:
            inputData = pickle.load(infile)
    else:
        raise ValueError("wrong input string")
    printInputData(inputData)
    return inputData
