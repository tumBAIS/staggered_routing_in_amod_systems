from __future__ import annotations

import copy
from collections import namedtuple
from enum import Enum

from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution


class NextEpochDeparturesComputer:
    changeMade = True
    departuresToModify: list[NextEpochDeparture] = []
    departuresToAdd: list[NextEpochDeparture] = []
    vehiclesToCheck: set[int] = []
    indicesDeparturesToModify: list[int] = []

    def run(self, nextEpochDepartures: list[NextEpochDeparture],
            currentEpochInstance: EpochInstance,
            currentEpochStatusQuo: EpochSolution,
            vehicleStatusList: list[VehicleStatus]) -> list[NextEpochDeparture]:
        self._resetAttributes()
        for firstNextEpochDepartureVehicle in nextEpochDepartures:
            if firstNextEpochDepartureVehicle.vehicle not in self.vehiclesToCheck:
                continue
            else:
                self.vehiclesToCheck.remove(firstNextEpochDepartureVehicle.vehicle)
            followingNextEpochDeparture = copy.deepcopy(firstNextEpochDepartureVehicle)
            while _isTimeInCurrentEpoch(followingNextEpochDeparture, currentEpochInstance):
                self._activateOtherConflictingVehicles(currentEpochStatusQuo, followingNextEpochDeparture,
                                                       currentEpochInstance, vehicleStatusList, nextEpochDepartures)
                if _isCurrentVehicleInSystem(followingNextEpochDeparture, currentEpochInstance):
                    followingNextEpochDeparture = _getFollowingNextEpochDeparture(currentEpochStatusQuo,
                                                                                  currentEpochInstance,
                                                                                  followingNextEpochDeparture)
                else:
                    break  # vehicle left the system
        self._applyChangesToNextEpochDepartures(vehicleStatusList, nextEpochDepartures)
        return nextEpochDepartures

    def _applyChangesToNextEpochDepartures(self, vehicleStatusList, nextEpochDepartures):
        for index, departureToModify in zip(self.indicesDeparturesToModify, self.departuresToModify):
            nextEpochDepartures[index] = departureToModify

        nextEpochDepartures += self.departuresToAdd
        for departureToAdd in self.departuresToAdd:
            vehicleStatusList[departureToAdd.vehicle] = VehicleStatus.ACTIVE

    def _updateNextEpochDepartureToAdd(self, otherVehicleInfo: OtherVehicleInfo, currentVehicle) -> None:
        indexDeparture, nextStoredEpochDeparture = _getStoredNextEpochDeparture(self.departuresToAdd,
                                                                                otherVehicleInfo.vehicle)
        if indexDeparture is None:
            # we are not adding the departure yet
            self.departuresToAdd.append(NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                           position=otherVehicleInfo.position,
                                                           time=otherVehicleInfo.departureTime,
                                                           arc=otherVehicleInfo.arc))
            self.changeMade = True
            self.vehiclesToCheck.add(otherVehicleInfo.vehicle)
            self.vehiclesToCheck.add(currentVehicle)
        else:
            # we are adding it already: let's check if we need to update it
            newDepartureIsEarlier = otherVehicleInfo.departureTime < nextStoredEpochDeparture.time
            if newDepartureIsEarlier:
                self.departuresToAdd[indexDeparture] = NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                                          position=otherVehicleInfo.position,
                                                                          time=otherVehicleInfo.departureTime,
                                                                          arc=otherVehicleInfo.arc)
                self.changeMade = True
                self.vehiclesToCheck.add(otherVehicleInfo.vehicle)
                self.vehiclesToCheck.add(currentVehicle)

    def _updateNextEpochDepartureToModify(self, activeNextEpochDepartures: list[NextEpochDeparture],
                                          otherVehicleInfo: OtherVehicleInfo, currentVehicle: int):
        indexDeparture, nextStoredEpochDeparture = _getStoredNextEpochDeparture(activeNextEpochDepartures,
                                                                                otherVehicleInfo.vehicle)

        newDepartureIsEarlier = otherVehicleInfo.departureTime < nextStoredEpochDeparture.time
        if newDepartureIsEarlier:
            if indexDeparture in self.indicesDeparturesToModify:
                alreadyInsertedDeparture = self.departuresToModify[
                    self.indicesDeparturesToModify.index(indexDeparture)]
                newDepartureIsEarlier2 = otherVehicleInfo.departureTime < alreadyInsertedDeparture.time
                if newDepartureIsEarlier2:
                    self.departuresToModify[
                        self.indicesDeparturesToModify.index(indexDeparture)] = \
                        NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                           position=otherVehicleInfo.position,
                                           time=otherVehicleInfo.departureTime,
                                           arc=otherVehicleInfo.arc)
                    self.changeMade = True
                    self.vehiclesToCheck.add(otherVehicleInfo.vehicle)
                    self.vehiclesToCheck.add(currentVehicle)

            else:
                self.indicesDeparturesToModify.append(indexDeparture)
                self.departuresToModify.append(NextEpochDeparture(vehicle=otherVehicleInfo.vehicle,
                                                                  position=otherVehicleInfo.position,
                                                                  time=otherVehicleInfo.departureTime,
                                                                  arc=otherVehicleInfo.arc))
                self.changeMade = True
                self.vehiclesToCheck.add(otherVehicleInfo.vehicle)
                self.vehiclesToCheck.add(currentVehicle)

    def _resetAttributes(self):
        self.departuresToModify = []
        self.departuresToAdd = []
        self.indicesDeparturesToModify = []
        self.changeMade = False

    def _initializeVehiclesToCheck(self, nextEpochDepartures: list[NextEpochDeparture]):
        self.vehiclesToCheck = {departure.vehicle for departure in nextEpochDepartures}

    def _activateOtherConflictingVehicles(self, currentEpochStatusQuo, followingNextEpochDeparture,
                                          currentEpochInstance, vehicleStatusList, nextEpochDepartures):
        otherVehiclesOnArc = [vehicle for vehicle in
                              currentEpochStatusQuo.vehiclesUtilizingArcs[followingNextEpochDeparture.arc] if
                              vehicle != followingNextEpochDeparture.vehicle]
        for otherVehicle in otherVehiclesOnArc:
            otherVehicleInfo = _getOtherVehicleInfo(currentEpochInstance,
                                                    currentEpochStatusQuo,
                                                    otherVehicle,
                                                    followingNextEpochDeparture.arc)
            if _isOtherConflicting(otherVehicleInfo, followingNextEpochDeparture):
                if vehicleStatusList[otherVehicle] == VehicleStatus.INACTIVE:
                    self._updateNextEpochDepartureToAdd(otherVehicleInfo, followingNextEpochDeparture.vehicle)

                elif vehicleStatusList[otherVehicle] == VehicleStatus.ACTIVE:
                    self._updateNextEpochDepartureToModify(nextEpochDepartures, otherVehicleInfo,
                                                           followingNextEpochDeparture.vehicle)


NextEpochDeparture = namedtuple("NextEpochDeparture", ["vehicle", "position", "time", "arc"])


def _getStoredNextEpochDeparture(departuresInNextEpoch, otherVehicle) -> tuple[int, NextEpochDeparture]:
    return next(
        ((i, departure) for i, departure in enumerate(departuresInNextEpoch) if
         _isSameVehicleDeparture(departure, otherVehicle)), (None, None))


OtherVehicleInfo = namedtuple("OtherVehicleInfo", ["departureTime", "arrivalTime", "position", "vehicle", "arc"])


def _getOtherVehicleInfo(currentEpochInstance: EpochInstance, currentEpochStatusQuo: EpochSolution,
                         otherVehicle: int,
                         arc: int) -> OtherVehicleInfo:
    otherPosition = currentEpochInstance.arcBasedShortestPaths[otherVehicle].index(arc)
    otherDepartureTime = currentEpochStatusQuo.congestedSchedule[otherVehicle][otherPosition]
    otherArrivalTime = currentEpochStatusQuo.congestedSchedule[otherVehicle][otherPosition + 1]
    return OtherVehicleInfo(departureTime=otherDepartureTime, arrivalTime=otherArrivalTime, position=otherPosition,
                            vehicle=otherVehicle, arc=arc)


def _isOtherConflicting(otherVehicleInfo, nextEpochDeparture):
    return otherVehicleInfo.departureTime <= nextEpochDeparture.time < otherVehicleInfo.arrivalTime


def _isTimeInCurrentEpoch(nextEpochDeparture, currentEpochInstance):
    return nextEpochDeparture.time / 60 < (currentEpochInstance.epochID + 1) * currentEpochInstance.inputData.epochSize


def _isCurrentVehicleInSystem(nextEpochDeparture, currentEpochInstance) -> bool:
    return nextEpochDeparture.position < len(
        currentEpochInstance.arcBasedShortestPaths[nextEpochDeparture.vehicle]) - 1


def _getFollowingNextEpochDeparture(currentEpochStatusQuo, currentEpochInstance,
                                    nextEpochDeparture) -> NextEpochDeparture:
    nextTime = currentEpochStatusQuo.congestedSchedule[nextEpochDeparture.vehicle][
        nextEpochDeparture.position + 1]
    nextArc = currentEpochInstance.arcBasedShortestPaths[nextEpochDeparture.vehicle][
        nextEpochDeparture.position + 1]
    return NextEpochDeparture(vehicle=nextEpochDeparture.vehicle,
                              position=nextEpochDeparture.position + 1,
                              time=nextTime,
                              arc=nextArc)


def _isSameVehicleDeparture(departureInNextEpoch: NextEpochDeparture, influentialVehicle: int) -> bool:
    return departureInNextEpoch.vehicle == influentialVehicle


DepartureInNextEpochDefaultValues = {"vehicle": -1, "position": -1, "time": -1, "arc": -1}


class VehicleStatus(Enum):
    ACTIVE = 1
    INACTIVE = 2
