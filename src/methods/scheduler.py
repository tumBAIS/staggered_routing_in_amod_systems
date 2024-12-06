import json
import typing

import scipy.special

import input_data
from problem.parameters import SolverParams
import utils.timer
from problem.trip import Trips
import cpp_module as cpp
from problem.network import Network
from pathlib import Path
import os


class Scheduler:

    def __init__(self, trips: Trips, network: Network, save_cpp_instance=False):
        self.trips = trips
        self.network = network
        self.cpp_solver_params = None
        self.cpp_instance = self.get_cpp_instance()
        self.save_cpp_instance_to_json("cpp_module/catch2_tests/instancesForTest/cpp_instance.json")
        self.cpp_scheduler = self._get_cpp_scheduler()
        if save_cpp_instance:
            self.save_cpp_instance_for_debugging()

    @utils.timer.timeit
    def py_construct_solution(self, start_times: list[float]) -> cpp.cpp_solution:
        """Cpp function that constructs a new solution from scratch"""
        solution = self.cpp_scheduler.construct_solution(start_times=start_times)
        # solution.print_solution_info(self.trips.get_number_of_trips_controlled(), name="Status quo")
        return solution

    @utils.timer.timeit
    def py_estimate_move_quality(self, solution: cpp.cpp_solution,
                                 route_id: int,
                                 new_departure_time: float,
                                 current_vehicle: int,
                                 trip_ids_on_arcs: list[list[int]],
                                 departure_times_on_arcs: list[list[float]],
                                 arrival_times_on_arcs: list[list[float]]
                                 ) -> bool:
        """Returns True if the new departure time is promising, False otherwise."""
        return self.cpp_scheduler.estimate_move_quality(new_departure_time=new_departure_time,
                                                        current_vehicle=current_vehicle,
                                                        route_id=route_id,
                                                        solution=solution,
                                                        trip_ids_on_arcs=trip_ids_on_arcs,
                                                        departure_times_on_arcs=departure_times_on_arcs,
                                                        arrival_times_on_arcs=arrival_times_on_arcs)

    # @staticmethod
    # def get_cpp_solver_params(solver_params: SolverParams) -> cpp.LNSSolverParams:
    #     # Validate mode
    #     mode = solver_params.mode
    #     if mode not in {"STAG", "BAL", "INTEG"}:
    #         raise RuntimeError("Mode is still undefined, todo")
    #
    #     # Extract relevant parameters
    #     max_no_improving_its = solver_params.LS_iterations
    #     goal = solver_params.goal
    #     max_cascade_level = solver_params.LS_max_cascade_level
    #     verbose = solver_params.verbose
    #     destroy_percentage = solver_params.LS_destroy_percentage
    #     ls_frequency = solver_params.LS_ls_frequency
    #     min_improvement = solver_params.LS_min_improvement
    #     improve_with_ls = solver_params.LS_improve_with_ls
    #
    #     # Return a well-structured cpp.LNSSolverParams object
    #     return cpp.LNSSolverParams(
    #         mode=mode,
    #         max_no_improving_its=max_no_improving_its,
    #         goal=goal,
    #         max_cascade_level=max_cascade_level,
    #         verbose=verbose,
    #         destroy_percentage=destroy_percentage,
    #         ls_frequency=ls_frequency,
    #         min_improvement=min_improvement,
    #         improve_with_ls=improve_with_ls
    #     )

    def get_cpp_instance(self) -> cpp.cpp_instance:
        """
        Constructs and returns a C++ instance by aggregating required data from trip and network models.
        """
        # Gather trip-specific data
        set_of_vehicle_routes = self.trips.get_vehicle_routes()
        release_times = self.trips.release_times
        parameters = [self.network.instance_params.algorithm_time_limit]

        # Gather network-specific data
        travel_times_arcs = self.network.travel_time_arcs
        capacities_arcs = self.network.nominal_capacities_arcs
        list_of_slopes = self.network.instance_params.list_of_slopes
        list_of_thresholds = self.network.instance_params.list_of_thresholds

        # Create and return the C++ instance
        return cpp.cpp_instance(
            set_of_vehicle_paths=set_of_vehicle_routes,
            travel_times_arcs=travel_times_arcs,
            capacities_arcs=capacities_arcs,
            list_of_slopes=list_of_slopes,
            list_of_thresholds=list_of_thresholds,
            parameters=parameters,
            release_times=release_times,
            lb_travel_time=self.trips.lb_travel_time
        )

    def save_cpp_instance_to_json(self, filename):
        # Construct a dictionary from the cpp_instance data using getter methods
        instance_data = {
            "set_of_vehicle_paths": self.cpp_instance.get_set_of_vehicle_paths(),
            "travel_times_arcs": self.cpp_instance.get_travel_times_arcs(),
            "capacities_arcs": self.cpp_instance.get_capacities_arcs(),
            "list_of_slopes": self.cpp_instance.get_list_of_slopes(),
            "list_of_thresholds": self.cpp_instance.get_list_of_thresholds(),
            "parameters": self.cpp_instance.get_parameters(),
            "release_times": self.cpp_instance.get_release_times()
        }

        # Serialize the dictionary to a JSON string
        with open(filename, 'w') as f:
            json.dump(instance_data, f, indent=4)

        print(f"Data saved to {filename}")

    def _get_cpp_scheduler(self):
        return cpp.cpp_scheduler(cpp_instance=self.cpp_instance)

    def save_cpp_instance_for_debugging(self):
        """
                Saves the current iteration state for debugging purposes in C++.

                Args:
                    trip (Trip): The trip being processed.
                """
        # Define the directory where the file will be saved
        path_to_repo = Path(__file__).parent.parent.parent
        path_to_file = path_to_repo / "cpp_module/validation_errors/schedule_mismatch/"
        os.makedirs(path_to_file, exist_ok=True)

        # Define the file name
        file_name = path_to_file / "last_cpp_instance_saved.json"

        # Prepare the error data for JSON serialization
        cpp_instance = {
            "controlled_flags": self.trips.controlled_flags,
            "deadlines": self.trips.deadlines,
            "release_times": self.trips.release_times,
            "routes_latest_departures": self.trips.routes_latest_departures,
            "free_flow_travel_matrix": self.trips.free_flow_travel_time_matrix,
            "lb_travel_time": self.trips.lb_travel_time,
            "lb_travel_time_controlled": self.trips.lb_travel_time_controlled,
            "list_of_slopes": self.network.instance_params.list_of_slopes,
            "list_of_thresholds": self.network.instance_params.list_of_thresholds,
            "max_cascade_level": -1,
            "set_of_vehicle_paths": self.trips.get_vehicle_routes(),
            "travel_time_arcs": self.network.travel_time_arcs,
            "nominal_capacities_arcs": self.network.nominal_capacities_arcs,
            "map_arc_trip_path_position": self.network.map_arc_trip_path_position
        }

        # Replace float('inf') with 'inf' in specific fields
        def replace_inf(data):
            if isinstance(data, list):
                return [replace_inf(item) for item in data]
            elif isinstance(data, dict):
                return {key: replace_inf(value) for key, value in data.items()}
            elif data == float('inf'):
                return "inf"
            else:
                return data

        # Write the error message to the file in JSON format
        with open(file_name, "w") as file:
            json.dump(cpp_instance, file, indent=4)

        print(f"Saved cpp_instance debugging file at {file_name}")
