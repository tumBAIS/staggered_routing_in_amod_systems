from __future__ import annotations

import datetime
from collections import Counter

import instance_module.instance
from instance_module.next_epoch_departures_computer import NextEpochDeparturesComputer, NextEpochDeparture, \
    VehicleStatus
from utils.classes import EpochSolution
from instance_module.epoch_instance import EpochInstance
from input_data import ACTIVATE_ASSERTIONS


def _get_departure_in_next_epoch(currentEpochInstance: EpochInstance, schedule: list[float]) -> \
        tuple[int, float] | tuple[None, None]:
    """Checks if there is an arrival occurring in the subsequent epoch, and returns the respective departure"""
    isInNextEpoch = lambda x: x / 60 > currentEpochInstance.input_data.epoch_size * (currentEpochInstance.epoch_id + 1)
    return next(
        ((position, departure) for position, departure in enumerate(schedule[:-1]) if
         isInNextEpoch(schedule[position + 1])), (None, None))


def _get_max_staggering_applicable_next_epoch(departure, globalInstance, nextEpochInstance, originalVehicleID) -> float:
    firstOriginalArc = globalInstance.trip_routes[originalVehicleID][0]
    arcIsOrigin = departure.arc == firstOriginalArc
    departureIsInNextEpoch = departure.time / 60 > nextEpochInstance.epoch_id * nextEpochInstance.input_data.epoch_size
    if arcIsOrigin and departureIsInNextEpoch:
        staggeringApplied = max(1e-2, departure.time - globalInstance.release_times_dataset[originalVehicleID])
        maxStaggeringApplicableNextEpoch = globalInstance.max_staggering_applicable[
                                               originalVehicleID] - staggeringApplied
    else:
        maxStaggeringApplicableNextEpoch = 1e-2  # to solve ties.
    return maxStaggeringApplicableNextEpoch


def _add_departures_to_next_epoch(nextEpochDepartures: list[NextEpochDeparture],
                                  currentEpochInstance: EpochInstance,
                                  nextEpochInstance: EpochInstance,
                                  globalInstance: instance_module.instance.Instance) -> None:
    for departure in nextEpochDepartures:
        originalVehicleID = currentEpochInstance.vehicles_original_ids[departure.vehicle]
        maxStaggeringApplicable = _get_max_staggering_applicable_next_epoch(departure, globalInstance,
                                                                            nextEpochInstance, originalVehicleID)
        lenPathNextEpoch = len(currentEpochInstance.trip_routes[departure.vehicle][departure.position:])
        pathToAppend = globalInstance.trip_routes[originalVehicleID][-lenPathNextEpoch:]
        lenTotalPath = len(currentEpochInstance.trip_routes[departure.vehicle])
        lenCurrentPath = lenTotalPath - lenPathNextEpoch

        nextEpochInstance.vehicles_original_ids.append(originalVehicleID)
        nextEpochInstance.max_staggering_applicable.append(maxStaggeringApplicable)
        nextEpochInstance.release_times.append(departure.time)
        nextEpochInstance.deadlines.append(globalInstance.deadlines[originalVehicleID])
        nextEpochInstance.trip_routes.append(pathToAppend)
        nextEpochInstance.last_position_for_reconstruction.append(None)
        currentEpochInstance.last_position_for_reconstruction[departure.vehicle] = lenCurrentPath


def _get_next_epoch_departures_active_vehicles(currentEpochStatusQuo: EpochSolution,
                                               currentEpochInstance: EpochInstance,
                                               vehicleStatusList: list[VehicleStatus]) -> list[NextEpochDeparture]:
    departuresInNextEpochActiveVehicles = []
    for vehicleEpochID, schedule in enumerate(currentEpochStatusQuo.congested_schedule):
        positionInNextEpoch, timeInNextEpoch = _get_departure_in_next_epoch(currentEpochInstance, schedule)
        if timeInNextEpoch is not None:
            vehicleStatusList[vehicleEpochID] = VehicleStatus.ACTIVE
            arcInNextEpoch = currentEpochInstance.trip_routes[vehicleEpochID][positionInNextEpoch]
            departuresInNextEpochActiveVehicles.append(NextEpochDeparture(vehicle=vehicleEpochID,
                                                                          position=positionInNextEpoch,
                                                                          time=timeInNextEpoch,
                                                                          arc=arcInNextEpoch))
    return departuresInNextEpochActiveVehicles


def _update_next_epoch_departures(currentEpochInstance: EpochInstance,
                                  currentEpochStatusQuo: EpochSolution,
                                  vehicleStatusList: list[VehicleStatus],
                                  activeNextEpochDepartures: list[NextEpochDeparture]) -> list[NextEpochDeparture]:
    nextEpochDeparturesComputer = NextEpochDeparturesComputer()
    while nextEpochDeparturesComputer.change_made:
        nextEpochDeparturesComputer._initialize_vehicles_to_check(activeNextEpochDepartures)
        activeNextEpochDepartures = \
            nextEpochDeparturesComputer.run(activeNextEpochDepartures,
                                            currentEpochInstance,
                                            currentEpochStatusQuo,
                                            vehicleStatusList)

    return activeNextEpochDepartures


def _assert_maximum_one_departure_for_vehicle(nextEpochDepartures: list[NextEpochDeparture]):
    if ACTIVATE_ASSERTIONS:
        vehiclesInNextEpochDepartures = [departure.vehicle for departure in nextEpochDepartures]
        counted_elements = Counter(vehiclesInNextEpochDepartures)
        repeated_elements = [item for item, count in counted_elements.items() if count > 1]
        assert repeated_elements == [], f"adding multiple departures for the same vehicle" \
                                        f"repeated elements: {repeated_elements}"


def update_next_epoch_instance(currentEpochInstance: EpochInstance,
                               currentEpochStatusQuo: EpochSolution,
                               nextEpochInstance: EpochInstance,
                               globalInstance: instance_module.instance.Instance):
    print("Updating next epoch departures...", end=" ")
    clock_start = datetime.datetime.now().timestamp()
    vehicleStatusList = [VehicleStatus.INACTIVE for _ in range(len(currentEpochStatusQuo.congested_schedule))]
    nextEpochDepartures = _get_next_epoch_departures_active_vehicles(currentEpochStatusQuo,
                                                                     currentEpochInstance,
                                                                     vehicleStatusList)

    nextEpochDepartures = _update_next_epoch_departures(currentEpochInstance, currentEpochStatusQuo,
                                                        vehicleStatusList, nextEpochDepartures)
    _assert_maximum_one_departure_for_vehicle(nextEpochDepartures)
    _add_departures_to_next_epoch(nextEpochDepartures, currentEpochInstance, nextEpochInstance, globalInstance)
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! time to update next epoch: {clock_end - clock_start:.2f}")
