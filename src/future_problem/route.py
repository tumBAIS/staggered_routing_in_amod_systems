from input_data import InstanceParameters
from utils.aliases import *
from utils.tools import pairwise
from future_problem.network import Network
from future_problem.arc import Arc
import random
from typing import TypeVar, Optional
from input_data import SPEED_KPH, InstanceParameters

Trip = TypeVar("Trip")  # Alias for trip


class TripRoute:

    def __init__(self, node_based_path: list[NodeID], network: Network, arg_route_id: int, trip: Trip,
                 instance_params: InstanceParameters):
        self.path_nodes = node_based_path  # nodes are integers starting from 0
        self.path_tuples_of_nodes = self._get_path_tuples_of_nodes()
        self.path_travel_time = self._get_path_travel_time(network)
        self.path_length_meters = self._get_path_length_meters(network)
        self.union_set_of_tuples_of_nodes_utilized = set()
        self.union_set_of_tuples_of_nodes_utilized.update(self.path_tuples_of_nodes)
        self.id = arg_route_id  # route id among alternative paths for given trip
        self.latest_departure = self.get_route_latest_departure(trip, instance_params.staggering_cap)
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
        return sum([network.G[origin][destination]["length"] * 3.6 / SPEED_KPH
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

    def get_route_latest_departure(self, trip: Trip, staggering_cap: float):
        """Get latest departure on route
        WARNING: we are losing control over the maximum staggering parameter.
        """
        assert 0 <= staggering_cap <= 100, "staggering cap is not correctly set"
        time_window = trip.deadline - trip.release_time
        slack = time_window - self.path_travel_time
        return trip.release_time + (slack * staggering_cap / 100)
