from __future__ import annotations

import copy
import datetime
import typing

import inputData
from dataclasses import dataclass, field


@dataclass
class EpochInstance:
    epochID: int
    inputData: inputData.InputData
    vehiclesOriginalIDS: list[int]
    releaseTimes: list[float]
    arcBasedShortestPaths: list[list[int]]
    deadlines: list[float]
    dueDates: list[float]
    maxStaggeringApplicable: list[float]
    travelTimesArcsUtilized: list[float]
    nominalCapacitiesArcs: list[float]
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
    arcBasedShortestPaths = copy.deepcopy(instance.arcBasedShortestPaths[firstVehicleInEpoch:lastVehicleInEpoch + 1])

    return EpochInstance(
        inputData=instance.inputData,
        vehiclesOriginalIDS=list(range(firstVehicleInEpoch, lastVehicleInEpoch + 1)),
        releaseTimes=instance.releaseTimesDataset[
                     firstVehicleInEpoch:lastVehicleInEpoch + 1],
        arcBasedShortestPaths=arcBasedShortestPaths,
        deadlines=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        maxStaggeringApplicable=instance.maxStaggeringApplicable[
                                firstVehicleInEpoch:lastVehicleInEpoch + 1],
        nominalCapacitiesArcs=instance.nominalCapacitiesArcs[:],
        travelTimesArcsUtilized=instance.travelTimesArcsUtilized[:],
        osmInfoArcsUtilized=instance.osmInfoArcsUtilized[:],
        lastPositionForReconstruction=[None for _ in
                                       instance.arcBasedShortestPaths[firstVehicleInEpoch:lastVehicleInEpoch + 1]],
        epochID=epochID,
        dueDates=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        startSolutionTime=datetime.datetime.now().timestamp(),
    )


def getEpochInstances(globalInstance) -> EpochInstances:
    epochSize = globalInstance.inputData.epochSize
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
