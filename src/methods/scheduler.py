import json
from future_problem.trip import Trips
import cpp_module as cpp
from future_problem.network import Network
from pathlib import Path
import os


class Scheduler:

    def __init__(self, trips: Trips, network: Network, save_cpp_instance=False):
        self.trips = trips
        self.network = network
        self.cpp_solver_params = None
        self.cpp_instance = self.get_cpp_instance()
        self.cpp_scheduler = self._get_cpp_scheduler()
        if save_cpp_instance:
            self.save_cpp_instance_for_debugging()

    def py_construct_solution(self, start_times: list[float]) -> cpp.cpp_solution:
        """Cpp function that constructs a new solution from scratch"""
        solution = self.cpp_scheduler.construct_solution(start_times=start_times)
        # solution.print_solution_info(self.trips.get_number_of_trips_controlled(), name="Status quo")
        return solution

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

    def get_cpp_instance(self) -> cpp.cpp_instance:
        """
        Constructs and returns a C++ instance by aggregating required data from trip and network models.
        """
        # Gather trip-specific data
        trip_routes = self.trips.get_vehicle_routes()
        release_times = self.trips.release_times
        parameters = [0]

        # Gather network-specific data
        travel_times_arcs = self.network.travel_time_arcs
        capacities_arcs = self.network.nominal_capacities_arcs
        list_of_slopes = self.network.instance_params.list_of_slopes
        list_of_thresholds = self.network.instance_params.list_of_thresholds

        # Create and return the C++ instance
        return cpp.cpp_instance(
            set_of_vehicle_paths=trip_routes,
            arc_position_in_routes_map=self.get_arc_position_in_routes_map(travel_times_arcs, trip_routes),
            travel_times_arcs=travel_times_arcs,
            capacities_arcs=capacities_arcs,
            list_of_slopes=list_of_slopes,
            list_of_thresholds=list_of_thresholds,
            parameters=parameters,
            release_times=release_times,
            lb_travel_time=self.trips.lb_travel_time,
            deadlines=self.initialize_deadlines(),
            conflicting_sets=self.initialize_conflicting_sets(travel_times_arcs),
            earliest_departures=self.initialize_earliest_departures(trip_routes),
            latest_departures=self.initialize_latest_departures(trip_routes),
        )

    @staticmethod
    def get_arc_position_in_routes_map(travel_times_arcs, trip_routes) -> list[list[int]]:
        """Maps the arc to the position in the trip routes. Used for efficient operations of local search"""
        arc_to_pos_map = [[-1 for _ in range(len(trip_routes))] for _ in
                          range(len(travel_times_arcs))]  # size of arcs

        for trip, route in enumerate(trip_routes):
            for position, arc in enumerate(route):
                if arc == 0:
                    continue
                arc_to_pos_map[arc][trip] = position

        return arc_to_pos_map

    def initialize_deadlines(self):
        return [float('inf')] * len(self.trips.deadlines)

    @staticmethod
    def initialize_conflicting_sets(travel_times):
        return [[] for arc in travel_times]

    @staticmethod
    def initialize_earliest_departures(trip_routes):
        return [[0 for _ in route] for route in trip_routes]

    @staticmethod
    def initialize_latest_departures(trip_routes):
        return [[float("inf") for _ in route] for route in trip_routes]

    def _get_cpp_scheduler(self):
        return cpp.cpp_scheduler(cpp_instance=self.cpp_instance)

    def save_cpp_instance_for_debugging(self):
        """
                Saves the current iteration state for debugging purposes in C++.
        """
        # Define the directory where the file will be saved
        path_to_repo = Path(__file__).parent.parent.parent
        path_to_file = path_to_repo / "cpp_module/validation_errors/schedule_mismatch/"
        os.makedirs(path_to_file, exist_ok=True)

        # Define the file name
        file_name = path_to_file / "last_cpp_instance_saved.json"

        # Prepare the error data for JSON serialization
        cpp_instance = {
            "deadlines": self.trips.deadlines,
            "release_times": self.trips.release_times,
            "routes_latest_departures": self.trips.routes_latest_departures,
            "free_flow_travel_matrix": self.trips.free_flow_travel_time_matrix,
            "lb_travel_time": self.trips.lb_travel_time,
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
