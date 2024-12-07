from typing import Optional, Union
from problem.parameters import InstanceParams, SPEED
from utils.aliases import *


class Arc:

    def __init__(self, id: ArcID, osm_info: Optional[OsmInfo] = None, is_dummy: bool = False):
        """
        Initialize an Arc. Use the class method `Arc.create_dummy_arc()` to create dummy arcs.
        """
        self.id = id
        self.is_dummy = is_dummy
        self.precomputed_delays = {}
        self.trips_potentially_using_arc = []  # Doesn't change
        self.trips_currently_using_arc = []  # Depends on the solution

        if not is_dummy:
            if osm_info is None:
                raise ValueError("osm_info must be provided for non-dummy arcs.")
            self.geometry = osm_info["geometry"]
            self.length = osm_info["length"]
            self.u_original = osm_info["u_original"]
            self.v_original = osm_info["v_original"]
            self.u_v_original = (self.u_original, self.v_original)
        else:
            self.geometry = None
            self.length = 0

    @classmethod
    def create_dummy_arc(cls, id: ArcID):
        """Factory method to create a dummy arc."""
        return cls(id=id, is_dummy=True)

    @property
    def nominal_travel_time(self):
        if self.is_dummy:
            return 0
        if self.length is None:
            raise AttributeError("Arc length is not set.")
        return self.length * 3.6 / SPEED

    @property
    def nominal_capacity(self):
        # Potentially a computed property in the future
        if self.is_dummy:
            return 0
        return 1  # Replace with logic if nominal capacity varies

    def __str__(self):
        return f"arc_{self.id}"

    def __repr__(self):
        return f"arc_{self.id}"

    def add_trip_currently_using_arc(self, trip):
        """Add trip to trips using arc"""
        if trip not in self.trips_currently_using_arc:
            self.trips_currently_using_arc.append(trip)

    def add_trip_potentially_using_arc(self, trip):
        """Add trip to trips using arc"""
        self.trips_potentially_using_arc.append(trip)

    def remove_trip_currently_using_arc(self, trip):
        """Remove trip from trips using arc"""
        if trip not in self.trips_currently_using_arc:
            raise RuntimeError("Removing non-existing trip.")
        self.trips_currently_using_arc.remove(trip)

    def get_delay(self, vehicles_on_arc):
        """Compute delay on arc according to an n-pieces latency function"""
        if self.is_dummy:
            return 0
        if vehicles_on_arc in self.precomputed_delays:
            return self.precomputed_delays[vehicles_on_arc]

        delay_at_pieces = [0]
        height_prev_piece = 0
        num_pieces = len(self.arc_slopes)

        for piece_id in range(num_pieces):
            slope = self.arc_slopes[piece_id]
            th_capacity = self.arc_thresholds[piece_id]

            if vehicles_on_arc > th_capacity:
                delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - th_capacity)
                delay_at_pieces.append(delay_current_piece)

            if piece_id < num_pieces - 1:
                next_th_cap = self.arc_thresholds[piece_id + 1]
                height_prev_piece += slope * (next_th_cap - th_capacity)

        max_delay = max(delay_at_pieces)
        self.precomputed_delays[vehicles_on_arc] = max_delay
        return max_delay

    def initialize_arc_slopes_and_thresholds(self, instance_params: InstanceParams):
        """Initialize arc slopes and thresholds."""
        self.arc_slopes = [self.nominal_travel_time * slope / self.nominal_capacity
                           for slope in instance_params.list_of_slopes]
        self.arc_thresholds = [threshold * self.nominal_capacity
                               for threshold in instance_params.list_of_thresholds]
