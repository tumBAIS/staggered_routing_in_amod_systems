from __future__ import annotations

import datetime

import conflicting_sets.split
from conflicting_sets.time_bounds import TimeBound, get_initial_latest_arrival_times, get_arc_based_time_bounds, \
    split_time_bounds_on_arcs, arrange_bounds_by_vehicle, get_undivided_conflicting_sets
from instanceModule.epoch_instance import EpochInstance
from instanceModule.instance import Instance
from utils.aliases import VehicleSchedules


def get_max_delay_on_arcs(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.maxDelayOnArc for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def get_min_delay_on_arcs(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.minDelayOnArc for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def get_earliest_departure_times(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.earliestDeparture for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def get_latest_departure_times(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.latestDeparture for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def add_conflicting_sets_to_instance(
        instance: Instance | EpochInstance,
        ffSchedule: VehicleSchedules) -> None:
    print("Adding undivided conflicting sets to instanceModule...", end=" ")
    clock_start = datetime.datetime.now().timestamp()
    knownLatestArrivalTimes = get_initial_latest_arrival_times(instance, ffSchedule)
    while True:
        arcBasedTimeBounds = get_arc_based_time_bounds(instance, knownLatestArrivalTimes, ffSchedule)
        boundsOnArcsSplit = split_time_bounds_on_arcs(instance, arcBasedTimeBounds)
        vehicleBasedTimeBounds = arrange_bounds_by_vehicle(arcBasedTimeBounds, instance.trip_routes)
        newLatestArrivalTimes = [[bound.latestArrival for bound in bounds] for bounds in vehicleBasedTimeBounds]
        if knownLatestArrivalTimes == newLatestArrivalTimes:
            break
        knownLatestArrivalTimes = newLatestArrivalTimes[:]

    instance.undivided_conflicting_sets = get_undivided_conflicting_sets(instance, boundsOnArcsSplit)
    instance.earliest_departure_times = get_earliest_departure_times(vehicleBasedTimeBounds)
    instance.latest_departure_times = get_latest_departure_times(vehicleBasedTimeBounds)
    instance.min_delay_on_arc = get_min_delay_on_arcs(vehicleBasedTimeBounds)
    instance.max_delay_on_arc = get_max_delay_on_arcs(vehicleBasedTimeBounds)

    conflicting_sets.split.split_conflicting_sets(instance)
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! - time necessary: {clock_end - clock_start:.2f} [s]")

    return
