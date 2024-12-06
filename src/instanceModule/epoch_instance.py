from __future__ import annotations

import copy
import datetime
import typing

from input_data import InputData
from dataclasses import dataclass, field


@dataclass
class EpochInstance:
    epoch_id: int
    input_data: InputData
    vehicles_original_ids: list[int]
    release_times: list[float]
    trip_routes: list[list[int]]
    deadlines: list[float]
    due_dates: list[float]
    max_staggering_applicable: list[float]
    travel_times_arcs: list[float]
    capacities_arcs: list[float]
    last_position_for_reconstruction: list[int | None]
    osm_info_arcs_utilized: list[dict[str:typing.Any]]  # type: ignore
    start_solution_time: float
    clock_start_epoch: float = field(default_factory=float)
    clock_end_epoch: float = field(default_factory=float)
    undivided_conflicting_sets: list[list[list[int]]] = field(default_factory=list[list[list[int]]])
    conflicting_sets: list[list[int]] = field(default_factory=list[list[int]])
    latest_departure_times: list[list[float]] = field(default_factory=list[list[float]])
    earliest_departure_times: list[list[float]] = field(default_factory=list[list[float]])
    min_delay_on_arc: list[list[float]] = field(default_factory=list[list[float]])
    max_delay_on_arc: list[list[float]] = field(default_factory=list[list[float]])
    removed_vehicles: list[int] = field(default_factory=list[int])

    def get_lb_travel_time(self) -> float:
        """Return sum of the free flow times of the routes of trips contained in instance"""
        return sum([self.travel_times_arcs[arc] for path in self.trip_routes for arc in path])


EpochInstances = list[EpochInstance]


def _get_last_vehicle_for_each_epoch(epochSize: int, releaseTimesDataset) -> list[int]:
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


def _get_epoch_instance(instance, epochID, firstVehicleInEpoch, lastVehicleInEpoch) -> EpochInstance:
    arcBasedShortestPaths = copy.deepcopy(instance.trip_routes[firstVehicleInEpoch:lastVehicleInEpoch + 1])

    return EpochInstance(
        input_data=instance.input_data,
        vehicles_original_ids=list(range(firstVehicleInEpoch, lastVehicleInEpoch + 1)),
        release_times=instance.release_times_dataset[
                      firstVehicleInEpoch:lastVehicleInEpoch + 1],
        trip_routes=arcBasedShortestPaths,
        deadlines=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        max_staggering_applicable=instance.max_staggering_applicable[
                                  firstVehicleInEpoch:lastVehicleInEpoch + 1],
        capacities_arcs=instance.capacities_arcs[:],
        travel_times_arcs=instance.travel_times_arcs[:],
        osm_info_arcs_utilized=instance.osm_info_arcs_utilized[:],
        last_position_for_reconstruction=[None for _ in
                                          instance.trip_routes[firstVehicleInEpoch:lastVehicleInEpoch + 1]],
        epoch_id=epochID,
        due_dates=instance.deadlines[firstVehicleInEpoch:lastVehicleInEpoch + 1],
        start_solution_time=datetime.datetime.now().timestamp(),
    )


def get_epoch_instances(globalInstance) -> EpochInstances:
    epochSize = globalInstance.input_data.epoch_size
    lastVehicleEpochs = _get_last_vehicle_for_each_epoch(epochSize, globalInstance.release_times_dataset)
    numberOfEpochs = len(lastVehicleEpochs)
    firstVehicleInEpoch = 0
    epochInstances = []
    for epoch in range(numberOfEpochs):
        lastVehicleInEpoch = lastVehicleEpochs[epoch]
        epochInstance = _get_epoch_instance(globalInstance, epoch, firstVehicleInEpoch, lastVehicleInEpoch)
        firstVehicleInEpoch = lastVehicleInEpoch + 1
        epochInstances.append(epochInstance)

    return epochInstances
