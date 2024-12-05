import datetime
import os
from dataclasses import dataclass
from pathlib import Path

# Import utilities
from utils.aliases import *  # Consider specifying which aliases are needed to avoid wildcard imports

# Set paths
path_to_repo: Path = Path(__file__).parent.parent.parent
path_to_instructions: Path = path_to_repo / "data/instructions"

# Date and time formatting
TODAY: str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Assertion activation
ACTIVATE_ASSERTIONS: bool = False
if ACTIVATE_ASSERTIONS:
    print("+-----------------------------------+")
    print("| >>>>>>>> ASSERTIONS ACTIVATED <<<< |")
    print("+-----------------------------------+")

# Tolerances
TOLERANCE: float = 1e-4
CONSTR_TOLERANCE: float = 1e-3

# Suppress Shapely warning, see: https://gis.stackexchange.com/q/397482
os.environ['USE_PYGEOS'] = '0'

# Constants
SPEED: int = 20  # Speed in kilometers per hou


@dataclass
class InstanceParams:
    network_name: str  # Name of the network to use (include .json extension)
    day: int  # Seed/Day used to sample data
    number_trips: int  # [applies for synthetic instances] Number of trips
    demand_factor: int  # [applies for real_world instances] Multiplies the existing trips
    list_of_slopes: list[float]  # List of slopes of pwl function
    list_of_thresholds: list[float]  # List of non-smooth threshold of pwl function
    staggering_cap: float  # [%] Cap of maximum staggering
    deadline_factor: float  # [%] Delta to extend deadline
    num_alternative_paths: int  # num alternative paths
    path_similarity_theta: float  # maximum similarity between alternative paths.
    kspwlo_algo: str  # maximum similarity between alternative paths.
    fraction_controlled: float  # 0 you do not control anything; 1 you control all the trips

    def __post_init__(self):

        if self.fraction_controlled > 1 or self.fraction_controlled < 0:
            raise ValueError(f"illegal fraction controlled {self.fraction_controlled}")

        # Add paths
        self._check_network_name()
        self._check_kspwlo_params()
        self.path_to_G = NodesPath(__file__).parent.parent.parent / f"data/{self.network_name}/network.json"
        self.path_to_routes = self.path_to_G.parent / f"{self.get_day_string()}{self.get_number_trips_string()}" \
                                                      f"K{self.num_alternative_paths}_{self._get_kspwlo_format_name()}_SIM{self.path_similarity_theta}/routes.json"
        self.path_to_instance = self.path_to_routes.parent / f"S{self.staggering_cap}_D{self.deadline_factor}_" \
                                                             f"VDF{self.list_of_slopes}{self.list_of_thresholds}_{self.fraction_controlled}Contr/instance.json"
        os.makedirs(self.path_to_instance.parent, exist_ok=True)

    def _check_kspwlo_params(self):
        possible_algos = ["onepass", "multipass", "svp_plus", "onepass_plus", "esx", "esx_complete",
                          "svp_plus_complete"]
        if self.kspwlo_algo not in possible_algos:
            raise RuntimeError(f"specify correct algo: {possible_algos}")
        if self.path_similarity_theta < 0 or self.path_similarity_theta > 1:
            raise RuntimeError("path_similarity_theta must be between 0 and 1.")

    def _get_kspwlo_format_name(self):
        if self.kspwlo_algo == "onepass":
            return "OP"
        elif self.kspwlo_algo == "multipass":
            return "MP"
        elif self.kspwlo_algo == "svp_plus":
            return "SVPP"
        elif self.kspwlo_algo == "onepass_plus":
            return "OPP"
        elif self.kspwlo_algo == "esx":
            return "ESX"
        elif self.kspwlo_algo == "esx_complete":
            return "ESXC"
        elif self.kspwlo_algo == "svp_plus_complete":
            return "SVPPC"
        else:
            raise ValueError(f"Unknown algorithm: {self.kspwlo_algo}")

    def get_name(self) -> str:
        input_data_name = ""
        for key, value in self.__dict__.items():
            if key in ["path_to_G", "path_to_instance", "path_to_routes"]:
                continue
            input_data_name += f"{str(value)}_"
        input_data_name = input_data_name[:-1].replace(":", "_")  # Remove trailing underscore and replace colons
        return input_data_name

    def get_number_trips_string(self) -> str:
        if "manhattan" in self.network_name:
            # real world
            if self.demand_factor <= 1:
                return ""
            else:
                return f"DF{self.demand_factor}_"
        else:
            # synthetic
            return f"T{self.number_trips}_"

    def get_day_string(self) -> str:
        if "manhattan" in self.network_name:
            return f"DAY{self.day}_"
        else:
            return ""

    def _check_network_name(self):
        if self.network_name == "pigou":
            return
        elif "lattice_" in self.network_name:
            name_split = self.network_name.split("_")
            assert len(name_split) == 2
            if name_split[0] != "lattice" or not isinstance(int(name_split[-1]), int):
                raise ValueError("invalid lattice network")
        elif "manhattan_" in self.network_name:
            name_split = self.network_name.split("_")
            assert len(name_split) == 2
            if name_split[0] != "manhattan" or not isinstance(int(name_split[-1]), int):
                raise ValueError("invalid manhattan network")


@dataclass
class SolverParams:
    instance_params: InstanceParams  # Instance parameters
    algo: str  # name of the model to utilize to get solution
    mode: str  # name of the model to utilize to get solution
    GA_seed: int  # seed to fix for solving instance
    GA_population_size: int  # [applies only for GA] size of initial population
    GA_parents_selection_mode: str  # [applies only for GA] mode to select parents
    GA_crossover_mode: str  # [applies only for GA] mode to obtain offspring thorugh crossover
    GA_iterations: int  # [applies only for GA] number of max_iters
    GA_offspring_operator: str  # [applies only for GA] mutation or education
    GA_penalization: float  # [applies only for GA] starting weight for penalization
    GA_it_pen: int  # [applies only for GA] number of max_iters after with we update weight
    GA_start_times_distribution: str  # [applies only for GA] distribution utilized to generate random start times
    LS_iterations: int  # [applies only for LS] max max_iters for LS.
    LS_max_cascade_level: int  # [applies only for LS] max cascading level for trip activation in cheap_evaluation.
    LS_destroy_percentage: float  # [applies only for LS] percentage of trips with delay to remove to destroy solution.
    LS_ls_frequency: float  # [applies only for LS] how often to call ls when constructing solution.
    LS_min_improvement: float  # [applies only for LS] minimum improvement to keep on destroying and repairing the solution.
    LS_improve_with_ls: float  # [applies only for LS] run ls after repair.
    plot_flag: bool  # plot figures in the search
    verbose: bool  # print messages during the search
    goal: str  # "WELFARE" minimizes the total travel time; "SELFISH" minimizes the total travel time of the controlled trips.
    set_of_experiments: Optional[str] = None  # name of the results subfolder for analysis (can be ignored.)
    start_time_optimization: Optional[float] = None

    def __post_init__(self):
        if self.algo not in ["GA", "LS", "None"]:
            raise ValueError(f"illegal algo parameter {self.algo}.")

        if self.mode not in ["STAG", "BAL", "BAL_STAG", "STAG_BAL", "INTEG", "None"]:
            raise ValueError(f"illegal mode parameter {self.mode}.")

        if self.goal not in ["WELFARE", "SELFISH"]:
            raise ValueError(f"illegal goal {self.goal}")

        if self.LS_max_cascade_level < -1:
            raise ValueError(f"illegal max_cascade_level {self.LS_max_cascade_level}")

        if self.LS_destroy_percentage > 1 or self.LS_destroy_percentage < 0:
            raise ValueError(f"illegal LS_destroy_percentage {self.LS_destroy_percentage}")

        if self.LS_min_improvement < 0 or self.LS_min_improvement > 1:
            raise ValueError(f"illegal LS_min_improvement {self.LS_min_improvement}")

        string_GA_params = self.safe_get_string_GA_params()
        string_LS_params = self.safe_get_string_LS_params()

        algo_mode = f"{self.algo}_{self.mode}"
        self.path_to_results_folder = self.instance_params.path_to_instance.parent / self.goal / algo_mode / string_GA_params / string_LS_params
        os.makedirs(self.path_to_results_folder, exist_ok=True)

    def get_name(self) -> str:
        input_data_name = ""
        for key, value in self.__dict__.items():
            if key in ["path_to_results_folder", "set_of_experiments", "instance_params", "start_time_optimization"]:
                continue
            input_data_name += f"{str(value)}_"
        input_data_name = input_data_name[:-1].replace(":", "_")  # Remove trailing underscore and replace colons
        return input_data_name

    def start_clock(self) -> None:
        self.start_time_optimization = datetime.datetime.now().timestamp()

    def _get_elapsed_algo_time(self) -> float:
        if self.start_time_optimization is None:
            raise ValueError("start time optimization is not initialized.")

        now = datetime.datetime.now().timestamp()
        return now - self.start_time_optimization

    def safe_get_string_GA_params(self) -> str:
        """Check if model selected is GA, check params
        :return string_GA_params: formatted string to indentify path experiment.
        """
        if "GA_" in self.algo:
            # Options for the genetic algorithm
            if self.GA_parents_selection_mode not in ["FIT"] and "ARY" not in self.GA_parents_selection_mode:
                raise ValueError("illegal parents selection mode")
            if self.GA_crossover_mode not in ["UN", "2P", "1P"]:
                raise ValueError("illegal crossover mode")
            if self.GA_start_times_distribution not in ["UN", "NOR"]:
                raise ValueError("illegal start time distribution")
            if self.GA_offspring_operator not in ["MUT", "EDU", "None"]:
                raise ValueError("illegal offspring operator.")

            string_GA_params = f"_{self.GA_seed}S_{self.GA_iterations}GAIT_{self.GA_population_size}POP_" \
                               f"{self.GA_penalization}PEN_{self.GA_it_pen}ITPEN_{self.GA_parents_selection_mode}Parents_" \
                               f"{self.GA_crossover_mode}Cross_{self.GA_start_times_distribution}" \
                               f"Distr_{self.GA_offspring_operator}"
        else:
            string_GA_params = ""
        return string_GA_params

    def safe_get_string_LS_params(self):
        if "LS_" in self.algo:
            string_LS_params = f"_{self.LS_iterations}LSIT"
        else:
            string_LS_params = ""
        return string_LS_params
