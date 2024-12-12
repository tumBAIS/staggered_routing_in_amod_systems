from __future__ import annotations

import copy
import datetime
from instance_module.instance import Instance
from input_data import SolverParameters, InstanceParameters
from typing import Optional


class EpochInstance(Instance):

    def __init__(
            self,
            epoch_id: int,
            input_data: InstanceParameters,
            vehicles_original_ids: list[int],
            release_times: list[float],
            trip_routes: list[list[int]],
            deadlines: list[float],
            max_staggering_applicable: list[float],
            capacities_arcs: list[int],  # Assuming capacities are keyed by arc ID
            travel_times_arcs: list[float],
            last_position_for_reconstruction: list[Optional[int]],  # Assuming last positions keyed by vehicle ID
    ) -> None:
        super().__init__(input_data=input_data, deadlines=deadlines,
                         trip_routes=trip_routes, travel_times_arcs=travel_times_arcs, capacities_arcs=capacities_arcs,
                         node_based_trip_routes=None, release_times=release_times)
        self.epoch_id = epoch_id
        self.vehicles_original_ids = vehicles_original_ids
        self.last_position_for_reconstruction = last_position_for_reconstruction
        self.start_solution_time = datetime.datetime.now().timestamp()
        self.max_staggering_applicable = max_staggering_applicable  # TODO: avoid this override.
        self.clock_start_epoch = None

    def start(self, epoch_size):
        print("=" * 60)
        print(f"Computing status quo for epoch {self.epoch_id} - "
              f"Epoch start time: {self.epoch_id * epoch_size * 60} [sec]".center(60))
        print("=" * 60)
        self.clock_start_epoch = datetime.datetime.now().timestamp()


EpochInstances = list[EpochInstance]


def get_last_vehicle_for_each_epoch(epoch_size: int, release_times_dataset: list[float]) -> list[int]:
    """
    Identify the last vehicle (trip) for each epoch based on release times.
    """
    num_epochs = 60 // epoch_size
    last_vehicle_epochs = []

    for epoch_id in range(num_epochs):
        start_time = epoch_id * epoch_size
        end_time = (epoch_id + 1) * epoch_size

        # Identify trips within the current epoch
        trips_in_epoch = [
            trip for trip, release_time in enumerate(release_times_dataset)
            if start_time <= release_time / 60 < end_time
        ]

        if trips_in_epoch:
            last_vehicle_epochs.append(trips_in_epoch[-1])  # Append the last trip in this epoch
        else:
            print(f"Epoch {epoch_id} ({start_time}-{end_time} minutes) has no trips and will be excluded.")

    print(f"Number of epochs with trips: {len(last_vehicle_epochs)}")
    return last_vehicle_epochs


def get_epoch_instance(instance, epoch_id, first_vehicle_in_epoch, last_vehicle_in_epoch) -> EpochInstance:
    arc_based_shortest_paths = copy.deepcopy(instance.trip_routes[first_vehicle_in_epoch:last_vehicle_in_epoch + 1])

    return EpochInstance(
        epoch_id=epoch_id,
        input_data=instance.input_data,
        vehicles_original_ids=list(range(first_vehicle_in_epoch, last_vehicle_in_epoch + 1)),
        release_times=instance.release_times[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
        trip_routes=arc_based_shortest_paths,
        deadlines=instance.deadlines[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
        max_staggering_applicable=instance.max_staggering_applicable[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
        capacities_arcs=instance.capacities_arcs[:],
        travel_times_arcs=instance.travel_times_arcs[:],
        last_position_for_reconstruction=[None for _ in range(last_vehicle_in_epoch + 1 - first_vehicle_in_epoch)])


def get_epoch_instances(global_instance: Instance, solver_params: SolverParameters) -> EpochInstances:
    """
    Create epoch instances from the global instance based on solver parameters.
    """
    last_vehicle_epochs = get_last_vehicle_for_each_epoch(
        solver_params.epoch_size, global_instance.release_times
    )
    epoch_instances = []

    first_vehicle_in_epoch = 0

    for epoch_id, last_vehicle_in_epoch in enumerate(last_vehicle_epochs):
        # Generate an epoch instance for the current epoch
        epoch_instance = get_epoch_instance(
            global_instance, epoch_id, first_vehicle_in_epoch, last_vehicle_in_epoch
        )
        epoch_instances.append(epoch_instance)

        # Update the first vehicle for the next epoch
        first_vehicle_in_epoch = last_vehicle_in_epoch + 1

    return epoch_instances
