import json
import os
from pathlib import Path

import networkx as nx
import numpy as np

import cpp_module as cpp
import instance_generator.real_world_graphs
import instance_generator.shortcuts
import utils.tools
from instance_generator import real_world_graphs as real_world_graphs, real_world_trips as real_world_trips
from instance_generator.network import Network
from instance_generator.trip import Trips
from input_data import InstanceParameters


class InstanceComputer:

    def __init__(self, input_data: InstanceParameters):
        """Initialize class to create instance files"""
        self.path_to_repo = Path(__file__).parent.parent.parent
        self.path_to_data = self.path_to_repo / "data"
        self.instance_params = input_data

    def run(self, plot_flag: bool = False):
        """Create instance associated to self.instance_params"""
        self._print_instance_generation()
        G = self._get_G(replace=False)
        network = Network(self.instance_params, G)
        self._compute_routes_file(network, replace=False)
        trips = Trips(self.instance_params, network, instance_available=False)
        network.add_arcs(trips)
        trips.set_network_paths(network)
        self.plot_paths(network, trips, plot_flag)
        # Construct status quo
        cpp_instance = self.get_cpp_instance(trips, network)
        cpp_scheduler = cpp.cpp_scheduler(cpp_instance)
        cpp_status_quo = cpp_scheduler.construct_solution(trips.get_release_times())

        from problem.solution import Solution
        py_status_quo = Solution.from_cpp_solution(cpp_status_quo, cpp_instance)
        py_status_quo.print_congestion_info()
        py_status_quo.print_delay_distributions()

        self._set_deadlines(trips, cpp_status_quo)
        self._save_instance_file(trips, cpp_status_quo)

    def get_cpp_instance(self, trips: Trips, network: Network) -> cpp.cpp_instance:
        """Create a CPP instance for the given epoch."""
        routes = trips.get_routes()
        travel_time_arcs = network.travel_time_arcs
        return cpp.cpp_instance(
            set_of_vehicle_paths=routes,
            arc_position_in_routes_map=self.get_arc_position_in_routes_map(travel_time_arcs, routes),
            travel_times_arcs=travel_time_arcs,
            capacities_arcs=network.nominal_capacities_arcs,
            list_of_slopes=self.instance_params.list_of_slopes,
            list_of_thresholds=self.instance_params.list_of_thresholds,
            parameters=[float("inf")],
            release_times=trips.get_release_times(),
            deadlines=trips.get_deadlines(),
            lb_travel_time=self.get_lb_travel_time(travel_time_arcs, routes),
            conflicting_sets=self.initialize_conflicting_sets(travel_time_arcs, routes),
            earliest_departures=self.initialize_earliest_departures(routes),
            latest_departures=self.initialize_latest_departures(routes)
        )

    def get_lb_travel_time(self, travel_times, trip_routes) -> float:
        return sum(travel_times[arc] for path in trip_routes for arc in path)

    @staticmethod
    def initialize_conflicting_sets(travel_times, routes):
        initial_conflicting_sets = [[] for _ in travel_times]
        for trip_id, route in enumerate(routes):
            for arc in route[:-1]:
                initial_conflicting_sets[arc].append(trip_id)
        return initial_conflicting_sets

    @staticmethod
    def initialize_earliest_departures(trip_routes):
        return [[0 for _ in route] for route in trip_routes]

    @staticmethod
    def initialize_latest_departures(trip_routes):
        return [[float("inf") for _ in route] for route in trip_routes]

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

    def _set_deadlines(self, trips: Trips, status_quo: cpp.cpp_solution):
        """Set deadlines to trips once computed status quo"""
        for trip in trips.R:
            trip.set_deadline(self._get_trip_deadline(trip, status_quo))
            trip.route.latest_departure = trip.route.get_route_latest_departure(trip,
                                                                                self.instance_params.staggering_cap)

    def _get_G(self, replace: bool = False) -> nx.DiGraph:
        """Import OSM graph. If replace is False, loads pre-serialized network, if it exists."""
        path_to_G = self.instance_params.path_to_G
        network_name = self.instance_params.network_name

        # Assuming path_to_repo is defined somewhere in your code
        path_to_repo = Path(__file__).parent.parent.parent
        relative_path_to_G = path_to_G.relative_to(path_to_repo)

        if os.path.exists(path_to_G) and not replace:
            print("\n" + "=" * 60)
            print(f"Loading pre-serialized network from: {relative_path_to_G}")
            print("-" * 60)
            G = utils.tools.deserialize(path_to_G)
        else:
            print("\n" + "=" * 60)
            print("Network not found or replace requested: creating a new one.")
            print("-" * 60)
            os.makedirs(path_to_G.parent, exist_ok=True)
            G = self._create_network_from_name(network_name, path_to_G, replace)

        print(f"Network '{network_name}' Summary")
        print("-" * 60)
        print(f"Number of Nodes: {len(G.nodes):>10}")
        print(f"Number of Edges: {len(G.edges):>10}")
        print("=" * 60 + "\n")

        return nx.DiGraph(G)

    def _create_network_from_name(self, network_name: str, path_to_G: Path, replace: bool) -> nx.DiGraph:
        """Create G based on network name."""
        if "manhattan" in network_name:
            return self._get_manhattan_network(network_name, replace, path_to_G)
        else:
            raise RuntimeError("Network type not implemented.")

    def _get_manhattan_network(self, network_name: str, replace: bool, path_to_G: Path) -> nx.DiGraph:
        """Get G of Manhattan (all of it or a percentage) and assign unique arc_id to each arc."""
        path_to_manhattan_G = self.path_to_data / "manhattan/network.json"
        percentage = int(network_name.split("_")[-1])

        # Step 1: Check if the Manhattan network exists, otherwise create it
        if os.path.exists(path_to_manhattan_G) and not replace:
            G_manhattan = utils.tools.deserialize(path_to_manhattan_G)
        else:
            os.makedirs(path_to_manhattan_G.parent, exist_ok=True)
            G_manhattan = real_world_graphs.get_G_from_osm_place("Manhattan, New York", path_to_manhattan_G)

        # Step 2: Get the southern percentage of the network
        G_percentage = real_world_graphs.get_southern_percentage_of_network(G_manhattan, percentage, path_to_G)
        if self.instance_params.add_shortcuts:
            instance_generator.shortcuts.add_shortcuts_to_graph(G_percentage)
            # Remove all arcs longer than 1 km
            edges_to_remove = [
                (u, v) for u, v, data in G_percentage.edges(data=True)
                if data.get("type_of_arc") == "shortcut" and data.get("length",
                                                                      0) > self.instance_params.max_length_shortcut
            ]
            G_percentage.remove_edges_from(edges_to_remove)

        G_percentage = nx.MultiDiGraph(G_percentage)
        instance_generator.real_world_graphs.plot_real_world_G(G_percentage,
                                                               path_to_G)  # Make sure this function can handle the relabeled graph
        utils.tools.serialize(G_percentage, path_to_G)  # Serialize the relabeled graph

        return nx.DiGraph(G_percentage)

    def _compute_routes_file(self, network: Network, replace: bool = False) -> None:
        """Compute a list of dictionaries (routes info) from which we build the instance trips."""

        # Calculate the relative path from the repository root
        path_to_repo = Path(__file__).parent.parent.parent  # Adjust this as per your project structure
        relative_path_to_routes = Path(self.instance_params.path_to_routes).relative_to(path_to_repo)

        if os.path.exists(self.instance_params.path_to_routes) and not replace:
            # Load the precomputed routes from the JSON file
            with open(self.instance_params.path_to_routes, 'r') as infile:
                routes_data = json.load(infile)

            # Summarize the generated trips
            num_trips = len(routes_data)
            trip_lengths = [route['path_length'] for route in routes_data]
            avg_trip_length = sum(trip_lengths) / num_trips if num_trips > 0 else 0
            unique_origins = set(route['origin'] for route in routes_data)
            unique_destinations = set(route['destination'] for route in routes_data)

            num_unique_origins = len(unique_origins)
            num_unique_destinations = len(unique_destinations)

            # Print the summary
            print("\n" + "=" * 60)
            print("Precomputed routes loaded successfully!")
            print(f"File Path: {relative_path_to_routes}")
            print("-" * 60)
            print(f"Total Number of Trips: {num_trips}")
            print(f"Average Trip Length (meters): {avg_trip_length:.2f}")
            print(f"Number of Unique Origins: {num_unique_origins}")
            print(f"Number of Unique Destinations: {num_unique_destinations}")
            print("=" * 60 + "\n")

            return

        network_name = self.instance_params.network_name
        print("\n" + "=" * 60)
        print(f"Generating routes info for network: {network_name}...")
        print("-" * 60 + "\n")

        routes_file = real_world_trips.get_real_world_trips(self.instance_params, network)

        self._save_routes_file(routes_file)

    def _save_instance_file(self, trips: Trips, solution: cpp.cpp_solution):
        # Copy the instance parameters and remove unnecessary keys
        params_dict = self.instance_params.__dict__.copy()
        keys_to_remove = ["path_to_G", "path_to_instance", "path_to_routes", "path_to_results"]

        for key_to_remove in keys_to_remove:
            if key_to_remove in params_dict:
                del params_dict[key_to_remove]

        # Prepare the information dictionary
        info = {
            "congestion_delay_sec": round(solution.get_total_delay(), 2),
            "travel_time_sec": round(solution.get_total_travel_time(), 2),
            "congestion_delay_min": round(solution.get_total_delay() / 60, 2),
            "travel_time_min": round(solution.get_total_travel_time() / 60, 2),
        }

        # Add the keys and values from params_dict to info
        info.update(params_dict)

        # Add trip information
        for trip in trips.R:
            trip_info = {
                "id": trip.id,
                "release_time": solution.get_trip_start_time(trip.id),
                "deadline": trip.deadline,
            }

            # Add path information for each trip
            path_info = {
                "latest_departure": round(trip.route.latest_departure, 2),
                "travel_time_sec": round(trip.route.path_travel_time, 2),
                "length_meters": round(trip.route.path_length_meters, 2),
                "num_arcs": trip.route.num_path_arcs
            }
            trip_info.update(path_info)

            info[f"trip_{trip.id}"] = trip_info

        # Ensure the directory exists before saving the file
        instance_dir = self.instance_params.path_to_instance.parent
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir, exist_ok=True)

        # Save the instance to a JSON file
        with open(self.instance_params.path_to_instance, "w") as outfile:
            json.dump(info, outfile, indent=4)

        # Calculate the relative path from the repository root
        path_to_repo = Path(__file__).parent.parent.parent  # Adjust this as per your project structure
        relative_path = Path(self.instance_params.path_to_instance).relative_to(path_to_repo)

        # Print the saved message with a pretty format
        print("\n" + "=" * 60)
        print(f"Instance saved successfully!")
        print(f"File Path: {relative_path}")
        print("=" * 60 + "\n")

    def _get_trip_deadline(self, trip, status_quo):
        """Get trip deadline based on the arrival in the status quo"""
        arrival = status_quo.get_trip_schedule(trip.id)[-1]
        congested_travel_time = arrival - trip.release_time
        extended_time = congested_travel_time * (1 + self.instance_params.deadline_factor / 100)
        return int(np.ceil(trip.release_time + extended_time))

    def _print_instance_generation(self):
        border = "=" * 60
        print(f"\n{border}")
        print(f"{'STARTING INSTANCE GENERATION':^60}")
        print(f"{border}\n")

        # Extract and pretty print instance parameters
        print(f"{'Instance Parameters':^60}")
        print("-" * 60)

        for key, value in vars(self.instance_params).items():
            if key in ["path_to_G", "path_to_routes", "path_to_instance"]:
                continue
            print(f"{key:<30}: {value}")

        print(f"\n{border}\n")

    def plot_paths(self, network: Network, trips: Trips, plot_flag: bool) -> None:
        """Create plot of paths to check if they make sense."""
        if not plot_flag:
            return
        if "manhattan" in self.instance_params.network_name:
            path_to_save = self.instance_params.path_to_instance
            trips_to_print = [0, 1]  # chosen casually
            paths = [path.path_nodes for trip_id in trips_to_print for path in trips.R[trip_id].route.P]
            real_world_graphs.plot_real_world_G(nx.MultiDiGraph(network.G), path_to_save, paths, plot_map=False)

    def _save_routes_file(self, routes_file: list[dict]) -> None:
        """Save routes file."""
        os.makedirs(self.instance_params.path_to_routes.parent, exist_ok=True)
        with open(self.instance_params.path_to_routes, "w") as f:
            json.dump(routes_file, f, indent=4)
