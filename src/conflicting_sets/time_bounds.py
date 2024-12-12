from __future__ import annotations
import copy
from queue import PriorityQueue
from input_data import ACTIVATE_ASSERTIONS, MIN_SET_CAPACITY, TOLERANCE
from instance_module.instance import Instance
from utils.aliases import *
from functools import total_ordering


@total_ordering
class TimeBound:
    def __init__(self, arc, vehicle, position, earliest_departure, latest_arrival, earliest_arrival,
                 latest_departure):
        self.arc = arc
        self.vehicle = vehicle
        self.position = position
        self.earliest_departure = earliest_departure
        self.latest_departure = latest_departure
        self.earliest_arrival = earliest_arrival
        self.latest_arrival = latest_arrival
        self.min_delay_on_arc = earliest_arrival - earliest_departure
        self.max_delay_on_arc = latest_arrival - earliest_departure

    @classmethod
    def complete(
            cls,
            arc,
            vehicle,
            position,
            earliest_departure,
            latest_departure,
            earliest_arrival,
            latest_arrival,
            min_delay_on_arc,
            max_delay_on_arc,
    ):
        """Create a TimeBound instance with all fields initialized."""
        time_bound = cls(arc, vehicle, position, earliest_departure, latest_arrival,
                         earliest_arrival, latest_departure)
        time_bound.min_delay_on_arc = min_delay_on_arc
        time_bound.max_delay_on_arc = max_delay_on_arc
        return time_bound

    def update_earliest_departure(self, new_value):
        self.earliest_departure = new_value

    def __eq__(self, other):
        if not isinstance(other, TimeBound):
            return NotImplemented
        # Two instances are equal if their earliest_departure is within TOLERANCE and vehicles are the same
        return (
                abs(self.earliest_departure - other.earliest_departure) < TOLERANCE
                and self.vehicle == other.vehicle
        )

    def __lt__(self, other):
        if not isinstance(other, TimeBound):
            return NotImplemented
        # Compare earliest_departure with TOLERANCE, then compare vehicles
        if abs(self.earliest_departure - other.earliest_departure) < TOLERANCE:
            return self.vehicle < other.vehicle
        return self.earliest_departure < other.earliest_departure


def split_time_bounds_on_arcs(instance: Instance, time_bounds_on_arcs: list[list[TimeBound]]) -> list[
    list[list[TimeBound]]]:
    """
    Splits time bounds on arcs into sets based on non-overlapping intervals.
    """
    bounds_on_arcs_split = [[] for _ in instance.travel_times_arcs]

    for arc, time_bounds in enumerate(time_bounds_on_arcs[1:], start=1):
        max_latest_arrival = float('-inf')
        bounds_split = []

        for vehicle_bounds in sorted(time_bounds, key=lambda x: x.earliest_departure):
            if vehicle_bounds.earliest_departure >= max_latest_arrival:
                if bounds_split:
                    bounds_on_arcs_split[arc].append(bounds_split)
                bounds_split = []
            bounds_split.append(vehicle_bounds)
            max_latest_arrival = max(max_latest_arrival, vehicle_bounds.latest_arrival)

        if bounds_split:
            bounds_on_arcs_split[arc].append(bounds_split)

    return bounds_on_arcs_split


def arrange_bounds_by_vehicle(arc_based_time_bounds: list[list[TimeBound]], paths: list[list[int]]) -> list[
    list[TimeBound]]:
    """
    Rearranges time bounds from arc-based to vehicle-based grouping.
    """
    vehicle_based_time_bounds: list[list[TimeBound]] = [[] for _ in paths]

    for arc, arc_time_bounds in enumerate(arc_based_time_bounds):
        for bound in arc_time_bounds:
            vehicle_based_time_bounds[bound.vehicle].append(bound)

    return [
        sorted(vehicle_bounds, key=lambda x: x.earliest_departure)
        for vehicle_bounds in vehicle_based_time_bounds
    ]


def compute_delay_on_arc(arc: int, instance: Instance, vehicles_on_arc: int) -> float:
    """
    Computes the delay on a given arc based on the number of vehicles present.
    """
    if arc == 0:
        return 0

    delay_at_pieces = [0]
    height_prev_piece = 0

    for i, threshold in enumerate(instance.instance_params.list_of_thresholds):
        th_capacity = threshold * instance.capacities_arcs[arc]
        slope = instance.travel_times_arcs[arc] * instance.instance_params.list_of_slopes[i] / instance.capacities_arcs[
            arc]

        if vehicles_on_arc > th_capacity:
            delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - th_capacity)
            delay_at_pieces.append(delay_current_piece)

        if i < len(instance.instance_params.list_of_slopes) - 1:
            next_th_cap = instance.instance_params.list_of_thresholds[i + 1] * instance.capacities_arcs[arc]
            height_prev_piece += slope * (next_th_cap - th_capacity)

    return max(delay_at_pieces)


def get_earliest_departures_list_and_pq(
        free_flow_schedule: TripSchedules,
        instance: Instance,
        known_latest_arrival_times,
) -> tuple[list[list[TimeBound]], PriorityQueue]:
    """
    Generates a list of earliest departures per arc and initializes a priority queue for processing.
    """
    # Initialize a priority queue and an empty list for arc-based earliest departures
    earliest_departures_priority_queue = PriorityQueue()
    arc_based_earliest_departures = [[] for _ in instance.travel_times_arcs]

    # Populate the arc-based earliest departures and priority queue
    for vehicle, schedule in enumerate(free_flow_schedule):
        for position, earliest_departure in enumerate(schedule):
            arc = instance.trip_routes[vehicle][position]
            latest_arrival = known_latest_arrival_times[vehicle][position]
            earliest_arrival = earliest_departure + instance.travel_times_arcs[arc]
            latest_departure = (
                earliest_departure + instance.max_staggering_applicable[vehicle]
                if position == 0
                else known_latest_arrival_times[vehicle][position - 1]
            )

            # Create a TimeBound instance
            departure = TimeBound(
                arc=arc,
                vehicle=vehicle,
                position=position,
                earliest_departure=earliest_departure,
                latest_departure=latest_departure,
                earliest_arrival=earliest_arrival,
                latest_arrival=latest_arrival,
            )

            # Add to arc-based list and priority queue
            arc_based_earliest_departures[arc].append(departure)
            if position == 0:
                earliest_departures_priority_queue.put(departure)

    # Sort each arc by earliest departure time and vehicle ID
    for arc in arc_based_earliest_departures:
        arc.sort(key=lambda x: (round(x.earliest_departure / TOLERANCE), x.vehicle))

    return arc_based_earliest_departures, earliest_departures_priority_queue


def propagate_min_delay(earliest_departures: list[list[TimeBound]], min_delay_on_this_arc: float,
                        departure: TimeBound, instance: Instance) -> None:
    """
    Propagates a minimum delay along the vehicle's route for subsequent arcs.
    """
    if min_delay_on_this_arc < 1e-6:
        return

    if departure.arc == 0:
        return  # No need to propagate delay for the last arc

    path = instance.trip_routes[departure.vehicle]
    current_position = path.index(departure.arc)

    indices_departures_next_arcs = {
        arc: next(
            id_ed for id_ed, ed in enumerate(earliest_departures[arc])
            if departure.vehicle == ed.vehicle
        )
        for arc in path[current_position + 1:]
    }

    for arc, index in indices_departures_next_arcs.items():
        new_time = earliest_departures[arc][index].earliest_departure + min_delay_on_this_arc
        earliest_departures[arc][index].update_earliest_departure(new_time)


def combine_conflicts(conflicting_arrivals: list[TimeBound], conflicting_departures: list[TimeBound]) -> list[
    tuple[float, str]]:
    """
    Combines conflicting arrivals and departures into a sorted list of events.
    """
    arrivals = [(arrival.latest_arrival, 'a') for arrival in conflicting_arrivals]
    departures = [(departure.earliest_departure, 'd') for departure in conflicting_departures]
    latest_arrivals = [(departure.latest_arrival, 'a') for departure in conflicting_departures]

    list_of_events = arrivals + departures + latest_arrivals
    return sorted(list_of_events, key=lambda x: x[0])


def get_conflicting_latest_arrivals(
        arc_based_arrivals: list[list[TimeBound]], earliest_departure: TimeBound
) -> list[TimeBound]:
    """
    Get conflicting latest arrivals for a given earliest departure.
    """
    return [
        arrival
        for arrival in arc_based_arrivals[earliest_departure.arc]
        if arrival.latest_arrival > earliest_departure.earliest_departure
    ]


def get_conflicting_departures(
        all_earliest_departures: list[list[TimeBound]],
        current_earliest_departure: TimeBound,
        current_latest_departure: float,
) -> list[TimeBound]:
    """
    Get a list of conflicting departures for a given departure event.

    A conflicting departure is one on the same arc, with a different vehicle, and whose earliest departure
    falls within the range of the current earliest and latest departure times.
    """
    # Extract departures for the current arc
    arc_departures = all_earliest_departures[current_earliest_departure.arc]

    # Find conflicting departures
    conflicting_departures = []
    for other_departure in arc_departures:
        is_different_vehicle = other_departure.vehicle != current_earliest_departure.vehicle
        is_within_time_window = (
                current_earliest_departure.earliest_departure
                <= other_departure.earliest_departure
                <= current_latest_departure
        )

        if is_different_vehicle and is_within_time_window:
            conflicting_departures.append(other_departure)

    return conflicting_departures


def assert_time_bound(time_bound: TimeBound) -> None:
    """
    Assert that a given time bound is valid based on arrival and departure times.
    """
    if ACTIVATE_ASSERTIONS:
        assert (
                time_bound.latest_arrival - time_bound.earliest_arrival > -1e-6
        ), f"TimeBoundError#1: Latest arrival <= Earliest arrival. Details: {time_bound}"
        assert (
                time_bound.latest_departure - time_bound.earliest_departure > -1e-6
        ), f"TimeBoundError#2: Latest departure <= Earliest departure. Details: {time_bound}"


def get_latest_departure(
        earliest_departure: TimeBound,
        instance: Instance,
        arc_based_time_bounds: list[list[TimeBound]]
) -> float:
    """
    Calculate the latest possible departure time for a given earliest departure.
    """
    if earliest_departure.position == 0:
        # First arc
        return earliest_departure.earliest_departure + instance.max_staggering_applicable[earliest_departure.vehicle]
    else:
        previous_arc = instance.trip_routes[earliest_departure.vehicle][earliest_departure.position - 1]
        previous_bound = next(
            (bound.latest_arrival for bound in arc_based_time_bounds[previous_arc]
             if bound.vehicle == earliest_departure.vehicle),
            None
        )
        return previous_bound


def get_earliest_arrival_time(
        conflicting_arrivals: list[TimeBound],
        current_latest_departure: float,
        instance: Instance,
        earliest_departure: TimeBound
) -> tuple[float, float]:
    """
    Calculate the earliest possible arrival time for a given departure.
    """
    arc_capacity_threshold = max(
        MIN_SET_CAPACITY,
        instance.capacities_arcs[earliest_departure.arc] * instance.instance_params.list_of_thresholds[0]
    )
    min_vehicles_on_arc = sum(
        1 for arrival in conflicting_arrivals
        if
        arrival.latest_departure < earliest_departure.earliest_departure and current_latest_departure < arrival.earliest_arrival
    ) + 1

    min_delay = compute_delay_on_arc(
        earliest_departure.arc, instance, min_vehicles_on_arc
    ) if min_vehicles_on_arc > arc_capacity_threshold else 0

    earliest_arrival_time = (
            earliest_departure.earliest_departure + min_delay + instance.travel_times_arcs[earliest_departure.arc]
    )
    return earliest_arrival_time, min_delay


def get_latest_arrival_time(
        conflicting_arrivals: list[TimeBound],
        conflicting_departures: list[TimeBound],
        earliest_departure: TimeBound,
        latest_departure_time: float,
        instance: Instance,
        known_latest_arrival_times: list[list[float]]
) -> tuple[float, float]:
    """
    Calculate the latest possible arrival time for a given departure event.
    """
    known_latest_arrival = known_latest_arrival_times[earliest_departure.vehicle][earliest_departure.position]
    nominal_travel_time = instance.travel_times_arcs[earliest_departure.arc]
    max_delay = 0.0

    sorted_events = combine_conflicts(conflicting_arrivals, conflicting_departures)
    current_latest_arrival = latest_departure_time + nominal_travel_time

    if not sorted_events:
        return min(known_latest_arrival, current_latest_arrival), 0

    vehicles_on_arc = len(conflicting_arrivals) + 1
    filtered_events = [
        event for event in sorted_events if not (event[1] == "a" and event[0] > latest_departure_time)
    ]
    filtered_events.append((latest_departure_time, "latest_departure"))

    for interval_end, event_type in filtered_events:
        delay = compute_delay_on_arc(earliest_departure.arc, instance, vehicles_on_arc)
        latest_arrival = interval_end + delay + nominal_travel_time

        if latest_arrival > current_latest_arrival:
            current_latest_arrival = copy.copy(latest_arrival)
        if delay > max_delay:
            max_delay = copy.copy(delay)

        vehicles_on_arc += 1 if event_type == "d" else -1 if event_type == "a" else 0

    return min(known_latest_arrival, current_latest_arrival), max_delay


def get_arc_based_time_bounds(
        instance: Instance,
        known_latest_arrival_times: TripSchedules,
        free_flow_schedule: TripSchedules
) -> list[list[TimeBound]]:
    """
    Computes time bounds for all arcs in the network based on earliest and latest departures and arrivals.
    """
    # Initialize data structures
    arc_based_time_bounds: list[list[TimeBound]] = [[] for _ in instance.travel_times_arcs]
    arc_based_earliest_departures, edpq = get_earliest_departures_list_and_pq(free_flow_schedule, instance,
                                                                              known_latest_arrival_times)

    while not edpq.empty():
        # Process the next earliest departure
        earliest_departure = edpq.get()
        latest_departure = get_latest_departure(earliest_departure, instance, arc_based_time_bounds)

        # Find conflicting arrivals and earliest departures
        conflicting_arrivals = get_conflicting_latest_arrivals(arc_based_time_bounds, earliest_departure)
        conflicting_earliest_departures = get_conflicting_departures(arc_based_earliest_departures,
                                                                     earliest_departure,
                                                                     latest_departure,
                                                                     )

        # Calculate earliest and latest arrival times
        earliest_arrival, min_delay_on_arc = get_earliest_arrival_time(
            conflicting_arrivals, latest_departure, instance, earliest_departure
        )
        propagate_min_delay(arc_based_earliest_departures, min_delay_on_arc, earliest_departure, instance)

        latest_arrival, max_delay_on_arc = get_latest_arrival_time(
            conflicting_arrivals,
            conflicting_earliest_departures,
            earliest_departure,
            latest_departure,
            instance,
            known_latest_arrival_times,
        )

        # Create and validate a new time bound
        time_bound = TimeBound.complete(
            arc=earliest_departure.arc,
            position=earliest_departure.position,
            vehicle=earliest_departure.vehicle,
            earliest_departure=earliest_departure.earliest_departure,
            latest_departure=latest_departure,
            earliest_arrival=earliest_arrival,
            latest_arrival=latest_arrival,
            min_delay_on_arc=min_delay_on_arc,
            max_delay_on_arc=max_delay_on_arc,
        )
        assert_time_bound(time_bound)

        # Append the time bound to the arc's list
        arc_based_time_bounds[earliest_departure.arc].append(time_bound)

        # Schedule the next departure if the vehicle continues traveling
        vehicle_is_traveling = instance.trip_routes[earliest_departure.vehicle][earliest_departure.position] != 0
        if vehicle_is_traveling:
            next_arc = instance.trip_routes[earliest_departure.vehicle][earliest_departure.position + 1]
            next_arc_travel_time = instance.travel_times_arcs[next_arc]
            next_earliest_departure = TimeBound(
                earliest_departure=earliest_arrival,
                arc=next_arc,
                vehicle=earliest_departure.vehicle,
                position=earliest_departure.position + 1,
                latest_arrival=known_latest_arrival_times[earliest_departure.vehicle][earliest_departure.position + 1],
                earliest_arrival=earliest_arrival + next_arc_travel_time,
                latest_departure=latest_arrival
            )
            edpq.put(next_earliest_departure)

    # Sort time bounds on each arc by earliest departure time
    arc_based_time_bounds = [
        sorted(time_bounds_on_arc, key=lambda x: x.earliest_departure)
        for time_bounds_on_arc in arc_based_time_bounds
    ]

    return arc_based_time_bounds


def get_initial_latest_arrival_times(instance: Instance, ff_schedule: TripSchedules) -> list[list[float]]:
    """
    The function calculates the latest arrival times for each vehicle at each stop,
    ensuring they respect the vehicle's deadline and account for available slack time.
    """
    assert len(instance.deadlines) == len(ff_schedule), "Mismatch in deadlines and free-flow schedule length."
    assert all(
        deadline + 1e-4 >= schedule[-1] for deadline, schedule in zip(instance.deadlines, ff_schedule)
    ), "Deadlines are inconsistent with schedules."

    return [[schedule[position] + instance.deadlines[vehicle] - schedule[-1] for position, _ in enumerate(schedule[:])
             ] for vehicle, schedule in enumerate(ff_schedule)]


def get_undivided_conflicting_sets(
        instance: Instance, bounds_on_arcs_split: list[list[list[TimeBound]]]
) -> UndividedConflictingSets:
    """
    Computes undivided conflicting sets for arcs based on the time bounds.
    """
    undivided_conflicting_sets = [
        [
            [time_bound.vehicle for time_bound in bounds_set]
            if len(bounds_set) > max(
                MIN_SET_CAPACITY, instance.capacities_arcs[arc] * instance.instance_params.list_of_thresholds[0]
            )
            else []
            for bounds_set in bounds_on_arc
        ]
        if arc > 0
        else []
        for arc, bounds_on_arc in enumerate(bounds_on_arcs_split)
    ]

    return undivided_conflicting_sets
