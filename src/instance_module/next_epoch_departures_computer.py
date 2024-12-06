from __future__ import annotations

import copy
from collections import namedtuple
from enum import Enum

from input_data import SolverParameters
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution


class NextEpochDeparturesComputer:
    change_made = True
    departures_to_modify: list[NextEpochDeparture] = []
    departures_to_add: list[NextEpochDeparture] = []
    vehicles_to_check: set[int] = []
    indices_departures_to_modify: list[int] = []

    def run(self, nextEpochDepartures: list[NextEpochDeparture],
            currentEpochInstance: EpochInstance,
            currentEpochStatusQuo: EpochSolution,
            vehicleStatusList: list[VehicleStatus],
            solver_params: SolverParameters) -> list[NextEpochDeparture]:
        self._reset_attributes()
        for firstNextEpochDepartureVehicle in nextEpochDepartures:
            if firstNextEpochDepartureVehicle.vehicle not in self.vehicles_to_check:
                continue
            else:
                self.vehicles_to_check.remove(firstNextEpochDepartureVehicle.vehicle)
            followingNextEpochDeparture = copy.deepcopy(firstNextEpochDepartureVehicle)
            while _is_time_in_current_epoch(followingNextEpochDeparture, currentEpochInstance, solver_params):
                self._activate_other_conflicting_vehicles(currentEpochStatusQuo, followingNextEpochDeparture,
                                                          currentEpochInstance, vehicleStatusList, nextEpochDepartures)
                if _is_current_vehicle_in_system(followingNextEpochDeparture, currentEpochInstance):
                    followingNextEpochDeparture = _get_following_next_epoch_departure(currentEpochStatusQuo,
                                                                                      currentEpochInstance,
                                                                                      followingNextEpochDeparture)
                else:
                    break  # vehicle left the system
        self._apply_changes_to_next_epoch_departures(vehicleStatusList, nextEpochDepartures)
        return nextEpochDepartures

    def _apply_changes_to_next_epoch_departures(self, vehicleStatusList, nextEpochDepartures):
        for index, departureToModify in zip(self.indices_departures_to_modify, self.departures_to_modify):
            nextEpochDepartures[index] = departureToModify

        nextEpochDepartures += self.departures_to_add
        for departureToAdd in self.departures_to_add:
            vehicleStatusList[departureToAdd.vehicle] = VehicleStatus.ACTIVE

    def _update_next_epoch_departure_to_add(self, otherVehicleInfo: OtherVehicleInfo, currentVehicle) -> None:
        indexDeparture, nextStoredEpochDeparture = _get_stored_next_epoch_departure(self.departures_to_add,
                                                                                    otherVehicleInfo.vehicle)
        if indexDeparture is None:
            # we are not adding the departure yet
            self.departures_to_add.append(NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                             position=otherVehicleInfo.position,
                                                             time=otherVehicleInfo.departureTime,
                                                             arc=otherVehicleInfo.arc))
            self.change_made = True
            self.vehicles_to_check.add(otherVehicleInfo.vehicle)
            self.vehicles_to_check.add(currentVehicle)
        else:
            # we are adding it already: let's check if we need to update it
            newDepartureIsEarlier = otherVehicleInfo.departureTime < nextStoredEpochDeparture.time
            if newDepartureIsEarlier:
                self.departures_to_add[indexDeparture] = NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                                            position=otherVehicleInfo.position,
                                                                            time=otherVehicleInfo.departureTime,
                                                                            arc=otherVehicleInfo.arc)
                self.change_made = True
                self.vehicles_to_check.add(otherVehicleInfo.vehicle)
                self.vehicles_to_check.add(currentVehicle)

    def _update_next_epoch_departure_to_modify(self, activeNextEpochDepartures: list[NextEpochDeparture],
                                               otherVehicleInfo: OtherVehicleInfo, currentVehicle: int):
        indexDeparture, nextStoredEpochDeparture = _get_stored_next_epoch_departure(activeNextEpochDepartures,
                                                                                    otherVehicleInfo.vehicle)

        newDepartureIsEarlier = otherVehicleInfo.departureTime < nextStoredEpochDeparture.time
        if newDepartureIsEarlier:
            if indexDeparture in self.indices_departures_to_modify:
                alreadyInsertedDeparture = self.departures_to_modify[
                    self.indices_departures_to_modify.index(indexDeparture)]
                newDepartureIsEarlier2 = otherVehicleInfo.departureTime < alreadyInsertedDeparture.time
                if newDepartureIsEarlier2:
                    self.departures_to_modify[
                        self.indices_departures_to_modify.index(indexDeparture)] = \
                        NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                           position=otherVehicleInfo.position,
                                           time=otherVehicleInfo.departureTime,
                                           arc=otherVehicleInfo.arc)
                    self.change_made = True
                    self.vehicles_to_check.add(otherVehicleInfo.vehicle)
                    self.vehicles_to_check.add(currentVehicle)

            else:
                self.indices_departures_to_modify.append(indexDeparture)
                self.departures_to_modify.append(NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                                    position=otherVehicleInfo.position,
                                                                    time=otherVehicleInfo.departureTime,
                                                                    arc=otherVehicleInfo.arc))
                self.change_made = True
                self.vehicles_to_check.add(otherVehicleInfo.vehicle)
                self.vehicles_to_check.add(currentVehicle)

    def _reset_attributes(self):
        self.departures_to_modify = []
        self.departures_to_add = []
        self.indices_departures_to_modify = []
        self.change_made = False

    def initialize_vehicles_to_check(self, nextEpochDepartures: list[NextEpochDeparture]):
        self.vehicles_to_check = {departure.vehicle for departure in nextEpochDepartures}

    def _activate_other_conflicting_vehicles(self, currentEpochStatusQuo, followingNextEpochDeparture,
                                             currentEpochInstance, vehicleStatusList, nextEpochDepartures):
        otherVehiclesOnArc = [vehicle for vehicle in
                              currentEpochStatusQuo.vehicles_utilizing_arcs[followingNextEpochDeparture.arc] if
                              vehicle != followingNextEpochDeparture.vehicle]
        for otherVehicle in otherVehiclesOnArc:
            otherVehicleInfo = _get_other_vehicle_info(currentEpochInstance,
                                                       currentEpochStatusQuo,
                                                       otherVehicle,
                                                       followingNextEpochDeparture.arc)
            if _is_other_conflicting(otherVehicleInfo, followingNextEpochDeparture):
                if vehicleStatusList[otherVehicle] == VehicleStatus.INACTIVE:
                    self._update_next_epoch_departure_to_add(otherVehicleInfo, followingNextEpochDeparture.vehicle)

                elif vehicleStatusList[otherVehicle] == VehicleStatus.ACTIVE:
                    self._update_next_epoch_departure_to_modify(nextEpochDepartures, otherVehicleInfo,
                                                                followingNextEpochDeparture.vehicle)


NextEpochDeparture = namedtuple("NextEpochDeparture", ["vehicle", "position", "time", "arc"])


def _get_stored_next_epoch_departure(departuresInNextEpoch, otherVehicle) -> tuple[int, NextEpochDeparture]:
    return next(
        ((i, departure) for i, departure in enumerate(departuresInNextEpoch) if
         _is_same_vehicle_departure(departure, otherVehicle)), (None, None))


OtherVehicleInfo = namedtuple("OtherVehicleInfo", ["departureTime", "arrivalTime", "position", "vehicle", "arc"])


def _get_other_vehicle_info(currentEpochInstance: EpochInstance, currentEpochStatusQuo: EpochSolution,
                            otherVehicle: int,
                            arc: int) -> OtherVehicleInfo:
    otherPosition = currentEpochInstance.trip_routes[otherVehicle].index(arc)
    otherDepartureTime = currentEpochStatusQuo.congested_schedule[otherVehicle][otherPosition]
    otherArrivalTime = currentEpochStatusQuo.congested_schedule[otherVehicle][otherPosition + 1]
    return OtherVehicleInfo(departureTime=otherDepartureTime, arrivalTime=otherArrivalTime, position=otherPosition,
                            vehicle=otherVehicle, arc=arc)


def _is_other_conflicting(otherVehicleInfo, nextEpochDeparture):
    return otherVehicleInfo.departureTime <= nextEpochDeparture.time < otherVehicleInfo.arrivalTime


def _is_time_in_current_epoch(nextEpochDeparture, currentEpochInstance, solver_params: SolverParameters):
    return nextEpochDeparture.time / 60 < (
            currentEpochInstance.epoch_id + 1) * solver_params.epoch_size


def _is_current_vehicle_in_system(nextEpochDeparture, currentEpochInstance) -> bool:
    return nextEpochDeparture.position < len(
        currentEpochInstance.trip_routes[nextEpochDeparture.vehicle]) - 1


def _get_following_next_epoch_departure(currentEpochStatusQuo, currentEpochInstance,
                                        nextEpochDeparture) -> NextEpochDeparture:
    nextTime = currentEpochStatusQuo.congested_schedule[nextEpochDeparture.vehicle][
        nextEpochDeparture.position + 1]
    nextArc = currentEpochInstance.trip_routes[nextEpochDeparture.vehicle][
        nextEpochDeparture.position + 1]
    return NextEpochDeparture(vehicle=nextEpochDeparture.vehicle,
                              position=nextEpochDeparture.position + 1,
                              time=nextTime,
                              arc=nextArc)


def _is_same_vehicle_departure(departureInNextEpoch: NextEpochDeparture, influentialVehicle: int) -> bool:
    return departureInNextEpoch.vehicle == influentialVehicle


DepartureInNextEpochDefaultValues = {"vehicle": -1, "position": -1, "time": -1, "arc": -1}


class VehicleStatus(Enum):
    ACTIVE = 1
    INACTIVE = 2
