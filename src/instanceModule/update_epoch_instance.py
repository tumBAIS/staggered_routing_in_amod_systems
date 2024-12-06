from __future__ import annotations

import datetime
from collections import Counter

import instanceModule.instance
from instanceModule.next_epoch_departures_computer import NextEpochDeparturesComputer, NextEpochDeparture, VehicleStatus
from utils.classes import EpochSolution
from instanceModule.epoch_instance import EpochInstance
from input_data import ACTIVATE_ASSERTIONS


def _getDepartureInNextEpoch(currentEpochInstance: EpochInstance, schedule: list[float]) -> \
        tuple[int, float] | tuple[None, None]:
    """Checks if there is an arrival occurring in the subsequent epoch, and returns the respective departure"""
    isInNextEpoch = lambda x: x / 60 > currentEpochInstance.input_data.epoch_size * (currentEpochInstance.epoch_id + 1)
    return next(
        ((position, departure) for position, departure in enumerate(schedule[:-1]) if
         isInNextEpoch(schedule[position + 1])), (None, None))


def _getMaxStaggeringApplicableNextEpoch(departure, globalInstance, nextEpochInstance, originalVehicleID) -> float:
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


def _addDeparturesToNextEpoch(nextEpochDepartures: list[NextEpochDeparture],
                              currentEpochInstance: EpochInstance,
                              nextEpochInstance: EpochInstance,
                              globalInstance: instanceModule.instance.Instance) -> None:
    for departure in nextEpochDepartures:
        originalVehicleID = currentEpochInstance.vehicles_original_ids[departure.vehicle]
        maxStaggeringApplicable = _getMaxStaggeringApplicableNextEpoch(departure, globalInstance,
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


def _getNextEpochDeparturesActiveVehicles(currentEpochStatusQuo: EpochSolution,
                                          currentEpochInstance: EpochInstance,
                                          vehicleStatusList: list[VehicleStatus]) -> list[NextEpochDeparture]:
    departuresInNextEpochActiveVehicles = []
    for vehicleEpochID, schedule in enumerate(currentEpochStatusQuo.congested_schedule):
        positionInNextEpoch, timeInNextEpoch = _getDepartureInNextEpoch(currentEpochInstance, schedule)
        if timeInNextEpoch is not None:
            vehicleStatusList[vehicleEpochID] = VehicleStatus.ACTIVE
            arcInNextEpoch = currentEpochInstance.trip_routes[vehicleEpochID][positionInNextEpoch]
            departuresInNextEpochActiveVehicles.append(NextEpochDeparture(vehicle=vehicleEpochID,
                                                                          position=positionInNextEpoch,
                                                                          time=timeInNextEpoch,
                                                                          arc=arcInNextEpoch))
    return departuresInNextEpochActiveVehicles


def _updateNextEpochDepartures(currentEpochInstance: EpochInstance,
                               currentEpochStatusQuo: EpochSolution,
                               vehicleStatusList: list[VehicleStatus],
                               activeNextEpochDepartures: list[NextEpochDeparture]) -> list[NextEpochDeparture]:
    nextEpochDeparturesComputer = NextEpochDeparturesComputer()
    while nextEpochDeparturesComputer.change_made:
        nextEpochDeparturesComputer._initializeVehiclesToCheck(activeNextEpochDepartures)
        activeNextEpochDepartures = \
            nextEpochDeparturesComputer.run(activeNextEpochDepartures,
                                            currentEpochInstance,
                                            currentEpochStatusQuo,
                                            vehicleStatusList)

    return activeNextEpochDepartures


def _assertMaximumOneDepartureForVehicle(nextEpochDepartures: list[NextEpochDeparture]):
    if ACTIVATE_ASSERTIONS:
        vehiclesInNextEpochDepartures = [departure.vehicle for departure in nextEpochDepartures]
        counted_elements = Counter(vehiclesInNextEpochDepartures)
        repeated_elements = [item for item, count in counted_elements.items() if count > 1]
        assert repeated_elements == [], f"adding multiple departures for the same vehicle" \
                                        f"repeated elements: {repeated_elements}"


def update_next_epoch_instance(currentEpochInstance: EpochInstance,
                               currentEpochStatusQuo: EpochSolution,
                               nextEpochInstance: EpochInstance,
                               globalInstance: instanceModule.instance.Instance):
    print("Updating next epoch departures...", end=" ")
    clock_start = datetime.datetime.now().timestamp()
    vehicleStatusList = [VehicleStatus.INACTIVE for _ in range(len(currentEpochStatusQuo.congested_schedule))]
    nextEpochDepartures = _getNextEpochDeparturesActiveVehicles(currentEpochStatusQuo,
                                                                currentEpochInstance,
                                                                vehicleStatusList)

    nextEpochDepartures = _updateNextEpochDepartures(currentEpochInstance, currentEpochStatusQuo,
                                                     vehicleStatusList, nextEpochDepartures)
    _assertMaximumOneDepartureForVehicle(nextEpochDepartures)
    _addDeparturesToNextEpoch(nextEpochDepartures, currentEpochInstance, nextEpochInstance, globalInstance)
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! time to update next epoch: {clock_end - clock_start:.2f}")
