import json
import os.path
import shapely as shp
from input_data import InstanceParameters
from future_problem.network import Network
from future_problem.route import TripRoute
from utils.aliases import *
import time


def _get_point_from_dict(point_dict: dict) -> shp.Point:
    return shp.Point(point_dict["x"], point_dict["y"])


class Trip:

    def __init__(self, network: Network, routes_info: dict, instance_params: InstanceParameters):
        """
        Initialize Trip object
        If given, contains for each trip a list of paths, represented as list of nodes.
        """
        # Properties
        self._origin_coords = _get_point_from_dict(routes_info["origin_coords"])
        self._destination_coords = _get_point_from_dict(routes_info["destination_coords"])
        self._origin = network.find_closest_node(self._origin_coords)
        self._destination = network.find_closest_node(self._destination_coords)
        self.id = int(routes_info["trip_id"])
        self._release_time = routes_info["release_time"]
        self._deadline: float = routes_info["deadline"]
        self._route = TripRoute(routes_info["path"], network, 0, self, instance_params)

    def __str__(self):
        return f"trip_{self.id}"

    def __repr__(self):
        return f"trip_{self.id}"

    def __lt__(self, other):
        return self.id < other.id

    @property
    def route(self):
        return self._route

    @property
    def release_time(self):
        return self._release_time

    @property
    def deadline(self):
        return self._deadline

    def initialize_current_path_and_departure(self):
        """Use as initial path simply the shortest path"""
        for arc in self.route.path_with_arcs:
            arc.add_trip_currently_using_arc(self)

    def set_deadline(self, deadline):
        self._deadline = deadline

    def get_free_flow_times_vector(self) -> list[float]:
        return [self.route.path_travel_time]


class Trips:

    def __init__(self, instance_params: InstanceParameters, network: Network, instance_available: bool = True):
        self.R = []
        routes_info_list = self._get_routes_from_file(instance_params)

        if instance_available:
            instance = self._load_instance(instance_params)
            self._add_deadlines_and_filter_routes(routes_info_list, instance)
        else:
            self._set_deadlines_to_inf(routes_info_list)

        for routes_info in routes_info_list:
            trip = Trip(network, routes_info, instance_params)
            self.R.append(trip)

        self.lb_travel_time = self._get_lb_travel_time()
        self.deadlines = [trip.deadline for trip in self.R]
        self.release_times = [trip.release_time for trip in self.R]
        self.routes_latest_departures = [[trip.route.latest_departure] for trip in self.R]
        self.free_flow_travel_time_matrix = self._get_free_flow_travel_time_matrix()

    @staticmethod
    def _get_routes_from_file(instance_params: InstanceParameters) -> RoutesFile:
        """
        Import precomputed routes from routes.json
        """
        if not os.path.exists(instance_params.path_to_routes):
            raise FileNotFoundError(f"no routes in {instance_params.path_to_routes}")
        with open(instance_params.path_to_routes, 'r') as file:
            return json.load(file)

    def get_osm_arcs_utilized(self) -> list[RelabeledNodesArcID]:
        """Return a list of osm arc ids utilized at least by one trip in one of its paths"""
        if self.R is not None:
            arcs_utilized = set()
            for trip in self.R:
                arcs_utilized.update(trip.route.union_set_of_tuples_of_nodes_utilized)
            return list(arcs_utilized)

    def _get_lb_travel_time(self) -> float:
        """Compute ideal travel time, obtained assuming no congestion and shortest paths"""
        lb_travel_time = 0
        for trip in self.R:
            lb_travel_time += trip.route.path_travel_time
        return lb_travel_time

    def get_vehicle_routes(self) -> list[list[int]]:
        """Returns complete collection of vehicle paths as list of list of ints."""
        return [trip.route.network_path_ids for trip in self.R]

    @staticmethod
    def _load_instance(instance_params, max_retries=5, delay=20) -> dict:
        """
        Load the instance from a JSON file, with file locking and retries.

        :param instance_params: Object containing path to the instance.
        :param max_retries: Maximum number of retries in case of JSONDecodeError or empty content.
        :param delay: Delay between retries in seconds.
        :return: Parsed instance as a dictionary.
        """
        if not os.path.exists(instance_params.path_to_instance):
            raise FileNotFoundError(f"The file {instance_params.path_to_instance} does not exist.")

        retries = 0
        while retries < max_retries:
            try:
                with open(instance_params.path_to_instance, "r") as f:
                    # Read the file content
                    content = f.read()

                    if not content.strip():
                        raise ValueError(f"The file {instance_params.path_to_instance} is empty.")

                    # Attempt to load the JSON content
                    instance = json.loads(content)
                    return instance
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}. Retrying in {delay} seconds... (Attempt {retries + 1}/{max_retries})")
                retries += 1
                time.sleep(delay)  # Wait before retrying
            except ValueError as e:
                print(f"Error: {e}. Retrying in {delay} seconds... (Attempt {retries + 1}/{max_retries})")
                retries += 1
                time.sleep(delay)  # Wait before retrying
            finally:
                # The file is automatically closed when the `with` block ends, no need for explicit unlock
                pass

        # If retries exhausted, raise an error
        raise Exception(f"Failed to load instance after {max_retries} attempts.")

    @staticmethod
    def _add_deadlines_and_filter_routes(routes_info_list: list[dict], instance: dict):
        for k, trip_info in instance.items():
            if isinstance(trip_info, dict):
                route_id = trip_info["id"]
                if route_id < len(routes_info_list):
                    routes_info_list[route_id]["deadline"] = trip_info["deadline"]
                    # Filter paths
                    path_count = sum(1 for key in trip_info if key.startswith("path_"))
                    routes_info_list[route_id]["paths"] = routes_info_list[route_id]["paths"][:path_count]
                else:
                    print(f"Warning: route_id {route_id} is out of bounds for routes_info_list.")

    def _get_free_flow_travel_time_matrix(self) -> list[list[float]]:
        """Construct matrix with free flow travel times of alternative routes
        The entries in the inner lists are sorted in ascending order
        :usages used to construct cpp_instance
        """
        free_flow_travel_time_matrix = [[] for _ in self.R]
        for trip in self.R:
            free_flow_travel_time_matrix[trip.id] = trip.get_free_flow_times_vector()
        return free_flow_travel_time_matrix

    def get_release_times(self) -> list[float]:
        return [trip.release_time for trip in self.R]

    @staticmethod
    def _set_deadlines_to_inf(routes_info_list):
        for route_info in routes_info_list:
            route_info["deadline"] = float("inf")

    def set_network_paths(self, network: Network):
        for trip in self.R:
            trip.route.set_network_path(network)
