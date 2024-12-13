from __future__ import annotations

import datetime
from collections import Counter

from input_data import SolverParameters, ACTIVATE_ASSERTIONS, CONSTR_TOLERANCE
from instance_module.epoch_instance import EpochInstance
from instance_module.next_epoch_departures_computer import NextEpochDeparturesComputer, NextEpochDeparture, \
    VehicleStatus
from utils.classes import Solution
import instance_module.instance


def get_departure_in_next_epoch(
        current_epoch_instance: EpochInstance,
        schedule: list[float],
        solver_params: SolverParameters
) -> tuple[int, float] | tuple[None, None]:
    """Find the first departure that occurs in the next epoch."""
    is_in_next_epoch = lambda x: x / 60 > solver_params.epoch_size * (current_epoch_instance.epoch_id + 1)
    return next(
        ((position, departure) for position, departure in enumerate(schedule[:-1]) if
         is_in_next_epoch(schedule[position + 1])),
        (None, None)
    )


def get_max_staggering_applicable_next_epoch(
        departure: NextEpochDeparture,
        global_instance: instance_module.instance.Instance,
        next_epoch_instance: EpochInstance,
        original_vehicle_id: int,
        solver_params: SolverParameters
) -> float:
    """Calculate the maximum staggering applicable for the next epoch."""
    first_original_arc = global_instance.trip_routes[original_vehicle_id][0]
    arc_is_origin = departure.arc == first_original_arc
    departure_is_in_next_epoch = departure.time / 60 > next_epoch_instance.epoch_id * solver_params.epoch_size

    if arc_is_origin and departure_is_in_next_epoch:
        staggering_applied = max(10 * CONSTR_TOLERANCE,
                                 departure.time - global_instance.release_times[original_vehicle_id])
        max_staggering = global_instance.max_staggering_applicable[original_vehicle_id] - staggering_applied
    else:
        max_staggering = 10 * CONSTR_TOLERANCE  # To resolve ties.

    return max_staggering


def add_departures_to_next_epoch(
        next_epoch_departures: list[NextEpochDeparture],
        current_epoch_instance: EpochInstance,
        next_epoch_instance: EpochInstance,
        global_instance: instance_module.instance.Instance,
        solver_params: SolverParameters
) -> None:
    """Add departures to the next epoch instance."""
    for departure in next_epoch_departures:
        original_vehicle_id = current_epoch_instance.vehicles_original_ids[departure.vehicle]
        max_staggering_applicable = get_max_staggering_applicable_next_epoch(
            departure, global_instance, next_epoch_instance, original_vehicle_id, solver_params
        )

        len_path_next_epoch = len(current_epoch_instance.trip_routes[departure.vehicle][departure.position:])
        path_to_append = global_instance.trip_routes[original_vehicle_id][-len_path_next_epoch:]
        len_current_path = len(current_epoch_instance.trip_routes[departure.vehicle]) - len_path_next_epoch

        next_epoch_instance.vehicles_original_ids.append(original_vehicle_id)
        next_epoch_instance.max_staggering_applicable.append(max_staggering_applicable)
        next_epoch_instance.release_times.append(departure.time)
        next_epoch_instance.deadlines.append(global_instance.deadlines[original_vehicle_id])
        next_epoch_instance.trip_routes.append(path_to_append)
        next_epoch_instance.last_position_for_reconstruction.append(None)
        current_epoch_instance.last_position_for_reconstruction[departure.vehicle] = len_current_path


def get_next_epoch_departures_active_vehicles(
        current_epoch_status_quo: Solution,
        current_epoch_instance: EpochInstance,
        vehicle_status_list: list[VehicleStatus],
        solver_params: SolverParameters
) -> list[NextEpochDeparture]:
    """Get active vehicle departures for the next epoch."""
    departures = []
    for vehicle_epoch_id, schedule in enumerate(current_epoch_status_quo.congested_schedule):
        position, time = get_departure_in_next_epoch(current_epoch_instance, schedule, solver_params)
        if time is not None:
            vehicle_status_list[vehicle_epoch_id] = VehicleStatus.ACTIVE
            arc = current_epoch_instance.trip_routes[vehicle_epoch_id][position]
            departures.append(NextEpochDeparture(vehicle=vehicle_epoch_id, position=position, time=time, arc=arc))
    return departures


def update_next_epoch_departures(
        current_epoch_instance: EpochInstance,
        current_epoch_status_quo: Solution,
        vehicle_status_list: list[VehicleStatus],
        active_departures: list[NextEpochDeparture],
        solver_params: SolverParameters
) -> list[NextEpochDeparture]:
    """Update departures for the next epoch."""
    departures_computer = NextEpochDeparturesComputer()
    while departures_computer.change_made:
        departures_computer.initialize_vehicles_to_check(active_departures)
        active_departures = departures_computer.run(
            active_departures, current_epoch_instance, current_epoch_status_quo, vehicle_status_list, solver_params
        )
    return active_departures


def assert_maximum_one_departure_for_vehicle(next_epoch_departures: list[NextEpochDeparture]) -> None:
    """Ensure that each vehicle has at most one departure in the next epoch."""
    if ACTIVATE_ASSERTIONS:
        vehicle_counts = Counter(departure.vehicle for departure in next_epoch_departures)
        repeated = [vehicle for vehicle, count in vehicle_counts.items() if count > 1]
        assert not repeated, f"Multiple departures for the same vehicle detected: {repeated}"


def update_next_epoch_instance(
        current_epoch_instance: EpochInstance,
        current_epoch_status_quo: Solution,
        next_epoch_instance: EpochInstance,
        global_instance: instance_module.instance.Instance,
        solver_params: SolverParameters
) -> None:
    """Update the next epoch instance based on the current epoch."""
    print("Updating next epoch departures...", end=" ")
    start_time = datetime.datetime.now().timestamp()

    vehicle_status_list = [VehicleStatus.INACTIVE for _ in range(len(current_epoch_status_quo.congested_schedule))]
    next_epoch_departures = get_next_epoch_departures_active_vehicles(
        current_epoch_status_quo, current_epoch_instance, vehicle_status_list, solver_params
    )

    next_epoch_departures = update_next_epoch_departures(
        current_epoch_instance, current_epoch_status_quo, vehicle_status_list, next_epoch_departures, solver_params
    )

    assert_maximum_one_departure_for_vehicle(next_epoch_departures)
    add_departures_to_next_epoch(next_epoch_departures, current_epoch_instance, next_epoch_instance, global_instance,
                                 solver_params)

    end_time = datetime.datetime.now().timestamp()
    print(f"done! Time to update next epoch: {end_time - start_time:.2f} seconds")
