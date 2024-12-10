from __future__ import annotations

import copy
import datetime
from instance_module.instance import Instance
from dataclasses import dataclass, field

from input_data import InstanceParameters


# @dataclass
# class EpochInstance:
#     epoch_id: int
#     input_data: InstanceParameters
#     vehicles_original_ids: list[int]
#     release_times: list[float]
#     trip_routes: list[list[int]]
#     deadlines: list[float]
#     due_dates: list[float]
#     max_staggering_applicable: list[float]
#     travel_times_arcs: list[float]
#     capacities_arcs: list[float]
#     last_position_for_reconstruction: list[int | None]
#     start_solution_time: float
#     clock_start_epoch: float = field(default_factory=float)
#     clock_end_epoch: float = field(default_factory=float)
#     undivided_conflicting_sets: list[list[list[int]]] = field(default_factory=lambda: [])
#     conflicting_sets: list[list[int]] = field(default_factory=list)
#     latest_departure_times: list[list[float]] = field(default_factory=list)
#     earliest_departure_times: list[list[float]] = field(default_factory=list)
#     min_delay_on_arc: list[list[float]] = field(default_factory=list)
#     max_delay_on_arc: list[list[float]] = field(default_factory=list)
#     removed_vehicles: list[int] = field(default_factory=list)
#
#     def get_lb_travel_time(self) -> float:
#         """Returns the sum of the free flow times of the routes of trips contained in the instance."""
#         return sum(self.travel_times_arcs[arc] for path in self.trip_routes for arc in path)

class EpochInstance(Instance):

    def __init__(self, epoch_id, input_data, vehicles_original_ids, release_times, trip_routes,
                 deadlines, max_staggering_applicable, capacities_arcs, travel_times_arcs,
                 last_position_for_reconstruction):
        super().__init__(input_data=input_data, deadlines=deadlines,
                         trip_routes=trip_routes, travel_times_arcs=travel_times_arcs, capacities_arcs=capacities_arcs,
                         node_based_trip_routes=None, release_times=release_times)
        self.epoch_id = epoch_id
        self.vehicles_original_ids = vehicles_original_ids
        self.last_position_for_reconstruction = last_position_for_reconstruction
        self.start_solution_time = datetime.datetime.now().timestamp()
        self.due_dates = self.deadlines
        self.max_staggering_applicable = max_staggering_applicable  # TODO: avoid this override.


EpochInstances = list[EpochInstance]


def _get_last_vehicle_for_each_epoch(epoch_size: int, release_times_dataset) -> list[int]:
    last_vehicle_epochs = []
    for epoch_id in range(int(60 / epoch_size)):
        trips_in_epoch = [trip for trip, release_time in enumerate(release_times_dataset) if
                          epoch_id * epoch_size <= release_time / 60 < (epoch_id + 1) * epoch_size]
        if trips_in_epoch:
            last_trip_in_epoch = trips_in_epoch[-1]
            last_vehicle_epochs.append(last_trip_in_epoch)
        else:
            print(f"Epoch {epoch_id} does not have any trips and will be excluded.")
    print(f"Number of epochs: {len(last_vehicle_epochs)}")
    return last_vehicle_epochs


def _get_epoch_instance(instance, epoch_id, first_vehicle_in_epoch, last_vehicle_in_epoch) -> EpochInstance:
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


def get_epoch_instances(global_instance, solver_params) -> EpochInstances:
    epoch_size = solver_params.epoch_size
    last_vehicle_epochs = _get_last_vehicle_for_each_epoch(epoch_size, global_instance.release_times)
    number_of_epochs = len(last_vehicle_epochs)
    first_vehicle_in_epoch = 0
    epoch_instances = []
    for epoch in range(number_of_epochs):
        last_vehicle_in_epoch = last_vehicle_epochs[epoch]
        epoch_instance = _get_epoch_instance(global_instance, epoch, first_vehicle_in_epoch, last_vehicle_in_epoch)
        first_vehicle_in_epoch = last_vehicle_in_epoch + 1
        epoch_instances.append(epoch_instance)

    return epoch_instances
