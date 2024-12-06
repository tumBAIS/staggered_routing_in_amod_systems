from __future__ import annotations

import copy
import datetime
import typing

import input_data
from dataclasses import dataclass, field


@dataclass
class EpochInstance:
    epochID: int
    inputData: inputData.InputData
    vehiclesOriginalIDS: list[int]
    releaseTimes: list[float]
    trip_routes: list[list[int]]
    deadlines: list[float]
    dueDates: list[float]
    maxStaggeringApplicable: list[float]
    travel_times_arcs: list[float]
    capacities_arcs: list[float]
    lastPositionForReconstruction: list[int | None]
    osmInfoArcsUtilized: list[dict[str:typing.Any]]  # type: ignore
    startSolutionTime: float
    clockStartEpoch: float = field(default_factory=float)
    clockEndEpoch: float = field(default_factory=float)
    undividedConflictingSets: list[list[list[int]]] = field(default_factory=list[list[list[int]]])
    conflictingSets: list[list[int]] = field(default_factory=list[list[int]])
    latestDepartureTimes: list[list[float]] = field(default_factory=list[list[float]])
    earliestDepartureTimes: list[list[float]] = field(default_factory=list[list[float]])
    minDelayOnArc: list[list[float]] = field(default_factory=list[list[float]])
    maxDelayOnArc: list[list[float]] = field(default_factory=list[list[float]])
    removedVehicles: list[int] = field(default_factory=list[int])

    def get_lb_travel_time(self) -> float:
        """Return sum of the free flow times of the routes of trips contained in instance"""
        return sum([self.travel_times_arcs[arc] for path in self.trip_routes for arc in path])


EpochInstances = list[EpochInstance]


def _getLastVehicleForEachEpoch(epochSize: int, releaseTimesDataset) -> list[int]:
    lastVehicleEpochs = []

    for epoch_ID in range(int(60 / epochSize)):
        trips_in_epoch = [trip for trip, releaseTime in enumerate(releaseTimesDataset) if
                          epoch_ID * epochSize <= releaseTime / 60 < (epoch_ID + 1) * epochSize]

        if trips_in_epoch:
            last_trip_in_epoch = trips_in_epoch[-1]
            lastVehicleEpochs.append(last_trip_in_epoch)
        else:
            print(f"Epoch {epoch_ID} does not have any trips and will be excluded.")
    print(f"Number of epochs: {len(lastVehicleEpochs)}")
    return lastVehicleEpochs


def _getEpochInstance(instance, epochID, firstVehicleInEpoch, lastVehicleInEpoch) -> EpochInstance:
    arcBasedShortestPaths = copy.deepcopy(instance.trip_routes[firstVehicleInEpoch:lastVehicleInEpoch + 1])

    return EpochInstance(
        inputData=instance.inputData,
        vehiclesOriginalIDS=list(range(firstVehicleInEpoch, lastVehicleInEpoch + 1)),
        releaseTimes=instance.releaseTimesDataset[
                     firstVehicleInEpoch:lastVehicleInEpoch + 1],
        trip_routes=arcBasedShortestPaths,
        deadlines=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        maxStaggeringApplicable=instance.maxStaggeringApplicable[
                                firstVehicleInEpoch:lastVehicleInEpoch + 1],
        capacities_arcs=instance.capacities_arcs[:],
        travel_times_arcs=instance.travel_times_arcs[:],
        osmInfoArcsUtilized=instance.osmInfoArcsUtilized[:],
        lastPositionForReconstruction=[None for _ in
                                       instance.trip_routes[firstVehicleInEpoch:lastVehicleInEpoch + 1]],
        epochID=epochID,
        dueDates=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        startSolutionTime=datetime.datetime.now().timestamp(),
    )


def get_epoch_instances(globalInstance) -> EpochInstances:
    epochSize = globalInstance.inputData.epoch_size
    lastVehicleEpochs = _getLastVehicleForEachEpoch(epochSize, globalInstance.releaseTimesDataset)
    numberOfEpochs = len(lastVehicleEpochs)
    firstVehicleInEpoch = 0
    epochInstances = []
    for epoch in range(numberOfEpochs):
        lastVehicleInEpoch = lastVehicleEpochs[epoch]
        epochInstance = _getEpochInstance(globalInstance, epoch, firstVehicleInEpoch, lastVehicleInEpoch)
        firstVehicleInEpoch = lastVehicleInEpoch + 1
        epochInstances.append(epochInstance)

    return epochInstances
