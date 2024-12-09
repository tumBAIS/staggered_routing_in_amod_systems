import json
import os.path
import random
import numpy as np
import shapely as shp
from input_data import InstanceParameters
from problem.network import Network
from problem.route import TripRoutes, TripRoute
from utils.aliases import *
import time
from typing import Optional


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
        self._routes = TripRoutes(self, network, routes_info["path"], instance_params)

        # Variables
        self._current_route: Optional[TripRoute] = None
        self._current_departure: Optional[float] = None

    def __str__(self):
        return f"trip_{self.id}"

    def __repr__(self):
        return f"trip_{self.id}"

    def __lt__(self, other):
        return self.id < other.id

    @property
    def dest_coord_dict(self):
        return {"x": self.destination_coords.x, "y": self.destination_coords.y}

    @property
    def origin_coord_dict(self):
        return {"x": self.origin_coords.x, "y": self.origin_coords.y}

    @property
    def origin(self):
        return self._origin

    @property
    def destination(self):
        return self._destination

    @property
    def routes(self):
        return self._routes

    @property
    def release_time(self):
        return self._release_time

    @property
    def deadline(self):
        return self._deadline

    @property
    def destination_coords(self):
        return self._destination_coords

    @property
    def origin_coords(self):
        return self._origin_coords

    @property
    def current_route(self) -> TripRoute:
        return self._current_route

    @property
    def current_departure(self):
        return self._current_departure

    def initialize_current_path_and_departure(self):
        """Use as initial path simply the shortest path"""
        self._current_route = self.routes.get_shortest_path()
        self._current_departure = self.release_time
        # Save trip in arc attribute
        for arc in self.current_route.path_with_arcs:
            arc.add_trip_currently_using_arc(self)

    def set_current_route_and_time(self, route: TripRoute, start_time: float):
        """Change the active path of the trip, but only update arcs that change"""
        # Get the old and new arc paths
        old_arcs = set(self.current_route.path_with_arcs)  # Convert to sets for faster comparison
        new_arcs = set(route.path_with_arcs)

        # Identify arcs that are being removed
        arcs_to_remove = old_arcs - new_arcs
        for arc in arcs_to_remove:
            arc.remove_trip_currently_using_arc(self)

        # Update path and departure
        self._current_route = route
        self._current_departure = start_time

        # Identify arcs that are being added
        arcs_to_add = new_arcs - old_arcs
        for arc in arcs_to_add:
            arc.add_trip_currently_using_arc(self)

    def get_random_start_time(self, distribution_type: str, target: float, route: TripRoute) -> float:
        """Return a start time between earliest and latest departure from origin.
        :param route: to get the start time.
        :param distribution_type: 'uniform' or 'normal'
        :param target: mean for the normal distribution
        """
        if distribution_type == "UN":
            return random.uniform(self.release_time, route.latest_departure)
        elif distribution_type == "NOR":
            # Calculate the range
            range_ = route.latest_departure - self.release_time

            # Set the standard deviation (using 1/4 of the range as an example)
            std = range_ / 4  # You can adjust this to be between range/4 to range/6

            # Attempt to generate a valid sample up to 10 times
            for _ in range(10):
                sample = np.random.normal(loc=target, scale=std)
                if self.release_time <= sample <= route.latest_departure:
                    return sample

            # If unable to generate a valid sample, return the release time
            return self.release_time

        else:
            raise ValueError("illegal distribution type.")

    def set_deadline(self, deadline):
        self._deadline = deadline

    def get_arc_position_current_route(self, arc_id: int):
        return self.current_route.arc_indices[arc_id]

    def get_free_flow_times_vector(self) -> list[float]:
        return [route.path_travel_time for route in self.routes.P]


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
        self.routes_latest_departures = [[route.latest_departure for route in trip.routes.P] for trip in self.R]
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
                arcs_utilized.update(trip.routes.union_set_of_tuples_of_nodes_utilized)
            return list(arcs_utilized)

    def set_trips_network_paths(self, network: Network):
        """Set the network path for every alternative path of every trip."""
        for trip in self.R:
            trip.routes.set_network_paths(network)
            trip.initialize_current_path_and_departure()

    def get_trip(self, id: int):
        """Trip is expected to be at position id. Check that: if true,
        continue, else find the object and raise warning"""

        return self.R[id]

    def change_current_paths_and_departures(self, ids_selected_routes: list[int], start_times: list[float]):
        """Change the current paths of every trip with a dict of updated paths"""
        for trip in self.R:
            selected_route = trip.routes.P[ids_selected_routes[trip.id]]
            trip.set_current_route_and_time(selected_route, start_times[trip.id])

    def _get_lb_travel_time(self) -> float:
        """Compute ideal travel time, obtained assuming no congestion and shortest paths"""
        lb_travel_time = 0
        for trip in self.R:
            lb_travel_time += trip.routes.shortest_path_travel_time
        return lb_travel_time

    def get_current_routes(self) -> dict[Trip, TripRoute]:
        """Return list of currently used paths"""
        return {trip: trip.current_route for trip in self.R}

    def get_current_routes_ids(self) -> list[int]:
        """Return list of currently used paths"""
        return [trip.current_route.id for trip in self.R]

    def get_current_start_times(self) -> list[float]:
        """Return list of currently used paths"""
        return [trip.current_departure for trip in self.R]

    def get_vehicle_routes(self) -> list[list[int]]:
        """Returns complete collection of vehicle paths as list of list of ints."""
        return [trip.routes.P[0].network_path_ids for trip in self.R]

    def _load_instance(self, instance_params, max_retries=5, delay=20) -> dict:
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

    def _set_deadlines_to_inf(self, routes_info_list):
        for route_info in routes_info_list:
            route_info["deadline"] = float("inf")
