from __future__ import annotations

import datetime
from collections import Counter

import instance_module.instance
from instance_module.next_epoch_departures_computer import NextEpochDeparturesComputer, NextEpochDeparture, \
    VehicleStatus
from utils.classes import EpochSolution
from instance_module.epoch_instance import EpochInstance
from input_data import ACTIVATE_ASSERTIONS


def get_departure_in_next_epoch(current_epoch_instance: EpochInstance, schedule: list[float]) -> tuple[int, float] | \
                                                                                                 tuple[None, None]:
    is_in_next_epoch = lambda x: x / 60 > current_epoch_instance.input_data.epoch_size * (
            current_epoch_instance.epoch_id + 1)
    return next(((position, departure) for position, departure in enumerate(schedule[:-1]) if
                 is_in_next_epoch(schedule[position + 1])), (None, None))


def get_max_staggering_applicable_next_epoch(departure, global_instance, next_epoch_instance,
                                             original_vehicle_id) -> float:
    first_original_arc = global_instance.trip_routes[original_vehicle_id][0]
    arc_is_origin = departure.arc == first_original_arc
    departure_is_in_next_epoch = departure.time / 60 > next_epoch_instance.epoch_id * next_epoch_instance.input_data.epoch_size
    if arc_is_origin and departure_is_in_next_epoch:
        staggering_applied = max(1e-2, departure.time - global_instance.release_times_dataset[original_vehicle_id])
        max_staggering_applicable_next_epoch = global_instance.max_staggering_applicable[
                                                   original_vehicle_id] - staggering_applied
    else:
        max_staggering_applicable_next_epoch = 1e-2  # to solve ties.
    return max_staggering_applicable_next_epoch


def add_departures_to_next_epoch(next_epoch_departures: list[NextEpochDeparture], current_epoch_instance: EpochInstance,
                                 next_epoch_instance: EpochInstance,
                                 global_instance: instance_module.instance.Instance) -> None:
    for departure in next_epoch_departures:
        original_vehicle_id = current_epoch_instance.vehicles_original_ids[departure.vehicle]
        max_staggering_applicable = get_max_staggering_applicable_next_epoch(departure, global_instance,
                                                                             next_epoch_instance, original_vehicle_id)
        len_path_next_epoch = len(current_epoch_instance.trip_routes[departure.vehicle][departure.position:])
        path_to_append = global_instance.trip_routes[original_vehicle_id][-len_path_next_epoch:]
        len_total_path = len(current_epoch_instance.trip_routes[departure.vehicle])
        len_current_path = len_total_path - len_path_next_epoch

        next_epoch_instance.vehicles_original_ids.append(original_vehicle_id)
        next_epoch_instance.max_staggering_applicable.append(max_staggering_applicable)
        next_epoch_instance.release_times.append(departure.time)
        next_epoch_instance.deadlines.append(global_instance.deadlines[original_vehicle_id])
        next_epoch_instance.trip_routes.append(path_to_append)
        next_epoch_instance.last_position_for_reconstruction.append(None)
        current_epoch_instance.last_position_for_reconstruction[departure.vehicle] = len_current_path


def get_next_epoch_departures_active_vehicles(current_epoch_status_quo: EpochSolution,
                                              current_epoch_instance: EpochInstance,
                                              vehicle_status_list: list[VehicleStatus]) -> list[NextEpochDeparture]:
    departures_in_next_epoch_active_vehicles = []
    for vehicle_epoch_id, schedule in enumerate(current_epoch_status_quo.congested_schedule):
        position_in_next_epoch, time_in_next_epoch = get_departure_in_next_epoch(current_epoch_instance, schedule)
        if time_in_next_epoch is not None:
            vehicle_status_list[vehicle_epoch_id] = VehicleStatus.ACTIVE
            arc_in_next_epoch = current_epoch_instance.trip_routes[vehicle_epoch_id][position_in_next_epoch]
            departures_in_next_epoch_active_vehicles.append(
                NextEpochDeparture(vehicle=vehicle_epoch_id, position=position_in_next_epoch, time=time_in_next_epoch,
                                   arc=arc_in_next_epoch))
    return departures_in_next_epoch_active_vehicles


def update_next_epoch_departures(current_epoch_instance: EpochInstance, current_epoch_status_quo: EpochSolution,
                                 vehicle_status_list: list[VehicleStatus],
                                 active_next_epoch_departures: list[NextEpochDeparture]) -> list[NextEpochDeparture]:
    next_epoch_departures_computer = NextEpochDeparturesComputer()
    while next_epoch_departures_computer.change_made:
        next_epoch_departures_computer.initialize_vehicles_to_check(active_next_epoch_departures)
        active_next_epoch_departures = next_epoch_departures_computer.run(active_next_epoch_departures,
                                                                          current_epoch_instance,
                                                                          current_epoch_status_quo, vehicle_status_list)

    return active_next_epoch_departures


def assert_maximum_one_departure_for_vehicle(next_epoch_departures: list[NextEpochDeparture]):
    if ACTIVATE_ASSERTIONS:
        vehicles_in_next_epoch_departures = [departure.vehicle for departure in next_epoch_departures]
        counted_elements = Counter(vehicles_in_next_epoch_departures)
        repeated_elements = [item for item, count in counted_elements.items() if count > 1]
        assert not repeated_elements, f"Adding multiple departures for the same vehicle with repeated elements: {repeated_elements}"


def update_next_epoch_instance(current_epoch_instance: EpochInstance, current_epoch_status_quo: EpochSolution,
                               next_epoch_instance: EpochInstance, global_instance: instance_module.instance.Instance):
    print("Updating next epoch departures...", end=" ")
    clock_start = datetime.datetime.now().timestamp()
    vehicle_status_list = [VehicleStatus.INACTIVE for _ in range(len(current_epoch_status_quo.congested_schedule))]
    next_epoch_departures = get_next_epoch_departures_active_vehicles(current_epoch_status_quo, current_epoch_instance,
                                                                      vehicle_status_list)

    next_epoch_departures = update_next_epoch_departures(current_epoch_instance, current_epoch_status_quo,
                                                         vehicle_status_list, next_epoch_departures)
    assert_maximum_one_departure_for_vehicle(next_epoch_departures)
    add_departures_to_next_epoch(next_epoch_departures, current_epoch_instance, next_epoch_instance, global_instance)
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! Time to update next epoch: {clock_end - clock_start:.2f} seconds")
