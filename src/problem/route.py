from utils.aliases import *
from utils.tools import pairwise
from problem.network import Network
from problem.arc import Arc
import random
from typing import TypeVar
from problem.parameters import SPEED
from problem.parameters import InstanceParams

Trip = TypeVar("Trip")  # Alias for trip


class TripRoute:

    def __init__(self, node_based_path: list[NodeID], network: Network, arg_route_id: int, trip: Trip,
                 instance_params: InstanceParams):
        self.path_nodes = node_based_path  # nodes are integers starting from 0
        self.path_tuples_of_nodes = self._get_path_tuples_of_nodes()
        self.path_travel_time = self._get_path_travel_time(network)
        self.path_length_meters = self._get_path_length_meters(network)
        self.id = arg_route_id  # route id among alternative paths for given trip
        self.latest_departure = self.get_latest_departure(trip, instance_params.staggering_cap)
        self.path_with_arcs: Optional[list[Arc]] = None
        self.arc_indices: Optional[dict[int:int]] = None  # maps an arc to its index in path
        self.network_path_ids: Optional[list[int]] = None
        self.num_path_arcs: Optional[int] = None

    def __str__(self):
        return f"path_{self.id}"

    def __repr__(self):
        return f"path_{self.id}"

    def _get_path_tuples_of_nodes(self) -> list[RelabeledNodesArcID]:
        return [(origin, destination) for origin, destination in pairwise(self.path_nodes)]

    def _get_path_travel_time(self, network) -> float:
        return sum([network.G[origin][destination]["length"] * 3.6 / SPEED
                    for origin, destination in self.path_tuples_of_nodes])

    def _get_path_length_meters(self, network) -> float:
        return sum([network.G[origin][destination]["length"] for origin, destination in self.path_tuples_of_nodes])

    def set_network_path(self, network: Network):
        """Add path with **network** arcs (different from osm arcs)"""
        self.network_path_ids = [network.arc_map[osm_arc] for osm_arc in self.path_tuples_of_nodes]
        # add final dummy arc
        self.network_path_ids.append(self.id)

        if self.path_with_arcs is not None:
            raise ValueError("overwriting path.")
        self.path_with_arcs = [network.get_arc_by_id(arc_id) for arc_id in self.network_path_ids]
        self.arc_indices = {arc.id: index for index, arc in enumerate(self.path_with_arcs)}
        self.num_path_arcs = len(self.path_with_arcs)

    def get_latest_departure(self, trip: Trip, staggering_cap: float):
        """Get latest departure on route
        WARNING: we are losing control over the maximum staggering parameter.
        """
        assert 0 <= staggering_cap <= 100, "staggering cap is not correclty set"
        time_window = trip.deadline - trip.release_time
        slack = time_window - self.path_travel_time
        return trip.release_time + (slack * staggering_cap / 100)


class TripRoutes:
    """Class regarding paths of a **single** trip"""

    def __init__(self, trip, network: Network, routes_nodes_list: list[list[NodeID]], instance_params: InstanceParams):
        """Initialize trip routes
        :param routes_nodes_list: list of list of node ids.
        """

        self.trip = trip  # store associated trip
        self.P = []
        self.union_set_of_tuples_of_nodes_utilized = set()

        for path_id, route_nodes in enumerate(routes_nodes_list):
            if not trip.controlled and path_id > 0:
                # if trip is not controlled, it will have only the shortest route
                break
            route = TripRoute(route_nodes, network, path_id, trip, instance_params)
            self.P.append(route)
            self.union_set_of_tuples_of_nodes_utilized.update(route.path_tuples_of_nodes)

        self._shortest_path_travel_time = min(self.P, key=lambda x: x.path_travel_time).path_travel_time
        self._longest_path_travel_time = max(self.P, key=lambda x: x.path_travel_time).path_travel_time

    def get_route_from_id(self, route_id: int) -> TripRoute:
        # Ensure that the route ID matches the expected position's ID in the list.
        try:
            return self.P[route_id]
        except:
            raise IndexError(f"Trip {self.trip.id} has the following routes: {self.P} "
                             f"Trying to access route at index {route_id}")

    @property
    def shortest_path_travel_time(self) -> float:
        """Return the shortest path travel time among alternative paths"""
        return self._shortest_path_travel_time

    def get_shortest_path(self) -> TripRoute:
        """Return the shortest path **object** among alternative paths"""
        return min(self.P, key=lambda x: x.path_travel_time)

    def set_network_paths(self, network: Network):
        """
        1) Set the network path for every alternative path of a **single** trip.
        2) Store which trips can potentially use the arc
        3) Store in which path you can find the arc (work as long as paths are disjoint.)
        """
        arc_id_found = set()
        for path in self.P:
            path.set_network_path(network)

            for arc in path.path_with_arcs:
                if arc.id in arc_id_found:
                    continue
                arc.add_trip_potentially_using_arc(self.trip)
                arc_id_found.add(arc.id)

    def get_random_route(self) -> TripRoute:
        if not self.P:  # Check if the list is empty
            raise ValueError("no paths in P")
        return random.choice(self.P)

    def get_path_containing_arc(self, arc: Arc) -> TripRoute:
        """Note: this works with disjoint paths"""
        for trip_path in self.P:
            if arc in trip_path.path_with_arcs:
                return trip_path
