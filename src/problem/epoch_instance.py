from __future__ import annotations

import copy
import datetime
from problem.instance import Instance
from input_data import SolverParameters, InstanceParameters, TOLERANCE
from typing import Optional


class EpochInstance(Instance):

    def __init__(
            self,
            epoch_id: int,
            instance: Instance,
            trip_original_ids: list[int],
            trip_ids_from_previous_epoch: Optional[list[int]],
            last_position_for_reconstruction: list[Optional[int]],  # Assuming last positions keyed by vehicle ID
    ) -> None:

        self.epoch_id = epoch_id
        self.trip_original_ids = trip_original_ids
        self.last_position_for_reconstruction = last_position_for_reconstruction
        self.clock_start_epoch = datetime.datetime.now().timestamp()
        self.clock_end_epoch = None
        self.removed_vehicles = []
        self.removed_arcs = []
        deadlines = [instance.deadlines[i] for i in trip_original_ids]
        trip_routes = [instance.trip_routes[i] for i in trip_original_ids]
        release_times = [instance.release_times[i] for i in trip_original_ids]
        max_staggering_applicable = [
            0 if trip_ids_from_previous_epoch and trip_id in trip_ids_from_previous_epoch else
            instance.max_staggering_applicable[trip_id]
            for trip_id in trip_original_ids
        ]
        super().__init__(instance_params=instance.instance_params, deadlines=deadlines,
                         trip_routes=trip_routes, travel_times_arcs=instance.travel_times_arcs,
                         capacities_arcs=instance.capacities_arcs, node_based_trip_routes=None,
                         release_times=release_times, max_staggering_applicable=max_staggering_applicable)

    def set_clock_end_epoch(self):
        self.clock_end_epoch = datetime.datetime.now().timestamp()

    def update_conflicting_sets_after_trip_removal(self) -> None:
        """
        Update conflicting sets with new TripIDs after vehicles are removed.
        """
        self.conflicting_sets = [
            [vehicle - sum(1 for removed in self.removed_vehicles if removed < vehicle) for vehicle in conf_set]
            for conf_set in self.conflicting_sets]

    def remove_arc_at_position_from_trip_route(self, trip, position, mode: str) -> None:
        """
        Remove an arc at a specific position from a trip route and update related attributes.
        """
        # Retrieve arc and travel time
        arc = self.trip_routes[trip][position]
        travel_time = self.travel_times_arcs[arc]

        # Remove the arc from the trip route
        self.trip_routes[trip].pop(position)

        # Adjust position index for timing-related attributes if mode is "last"
        timing_position = position + 1 if mode == "last" else position

        # Update timing and delay attributes
        self.latest_departure_times[trip].pop(timing_position)
        self.earliest_departure_times[trip].pop(timing_position)
        self.max_delay_on_arcs[trip].pop(timing_position)
        self.min_delay_on_arcs[trip].pop(timing_position)

        # Adjust release times or deadlines based on the mode
        if mode == "first":
            self.release_times[trip] += travel_time
        elif mode == "last":
            self.deadlines[trip] -= travel_time

    def remove_trip(self, trip):
        self.max_staggering_applicable.pop(trip)
        self.trip_routes.pop(trip)
        self.latest_departure_times.pop(trip)
        self.earliest_departure_times.pop(trip)
        self.max_delay_on_arcs.pop(trip)
        self.min_delay_on_arcs.pop(trip)
        self.deadlines.pop(trip)
        self.release_times.pop(trip)
        self.removed_vehicles.append(trip)

    def print_start(self, epoch_size):
        print("=" * 60)
        print(f"Starting epoch {self.epoch_id} - "
              f"time offset: {self.epoch_id * epoch_size * 60} [sec]".center(60))
        print("=" * 60)

    def get_trip_original_id(self, trip_id):
        return self.trip_original_ids[trip_id]

    def get_trip_id_before_simplification(self, simplified_trip_id: int) -> int:
        """
        Given a simplified_trip_id in the current list, return the original index
        before any integers were removed.

        Args:
            simplified_trip_id (int): The index in the simplified list.

        Returns:
            int: The original index before the list was simplified.
        """
        # Start with the simplified_trip_id
        original_id = simplified_trip_id

        # Iterate through the removed vehicles
        for removed_id in sorted(self.removed_vehicles):
            # If the removed_id is less than or equal to the current original_id,
            # it means the original_id must shift forward by one.
            if removed_id <= original_id:
                original_id += 1

        return original_id

    def get_arc_id_before_simplification(self, simplified_arc_id: int) -> int:
        """
        Given a simplified_arc_id in the current list, return the original index
        before any integers were removed.

        Args:
            simplified_arc_id (int): The index in the simplified list.

        Returns:
            int: The original index before the list was simplified.
        """
        # Start with the simplified_arc_id
        original_id = simplified_arc_id

        # Sort the removed arcs to ensure proper adjustment order
        sorted_removed_arcs = sorted(self.removed_arcs)

        # Debug: Print the simplified_arc_id and removed_arcs
        print(f"Simplified Arc ID: {simplified_arc_id}")
        print(f"Removed Arcs: {sorted_removed_arcs}")

        # Iterate through the removed arcs to adjust the original_id
        for removed_id in sorted_removed_arcs:
            # Debug: Print the current removed_id and original_id
            print(f"Checking Removed ID: {removed_id}, Current Original ID: {original_id}")

            # If the removed_id is less than or equal to the current original_id,
            # increment the original_id because this element was removed earlier.
            if removed_id <= original_id:
                original_id += 1

        # Debug: Print the final computed original_id
        print(f"Final Original ID: {original_id}")

        return original_id

    def merge_arc_sequence_in_trip_route(self, arc_sequence_to_merge: list[int], trip: int, start_idx: int,
                                         end_idx: int) -> None:
        merged_travel_time = sum(self.travel_times_arcs[arc] for arc in arc_sequence_to_merge)
        self.travel_times_arcs.append(merged_travel_time)
        self.capacities_arcs.append(1)  # Conflict cannot happen
        self.conflicting_sets.append([])
        merged_arc_id = len(self.travel_times_arcs) - 1

        del self.latest_departure_times[trip][start_idx + 1:end_idx + 1]
        del self.earliest_departure_times[trip][start_idx + 1:end_idx + 1]
        del self.max_delay_on_arcs[trip][start_idx + 1:end_idx + 1]
        del self.min_delay_on_arcs[trip][start_idx + 1:end_idx + 1]

        del self.trip_routes[trip][start_idx:end_idx + 1]
        self.trip_routes[trip].insert(start_idx, merged_arc_id)


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


#
# def get_epoch_instance(instance, epoch_id, first_vehicle_in_epoch, last_vehicle_in_epoch) -> EpochInstance:
#     arc_based_shortest_paths = copy.deepcopy(instance.trip_routes[first_vehicle_in_epoch:last_vehicle_in_epoch + 1])
#
#     return EpochInstance(
#         epoch_id=epoch_id,
#         instance_params=instance.instance_params,
#         vehicles_original_ids=list(range(first_vehicle_in_epoch, last_vehicle_in_epoch + 1)),
#         release_times=instance.release_times[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
#         trip_routes=arc_based_shortest_paths,
#         deadlines=instance.deadlines[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
#         max_staggering_applicable=instance.max_staggering_applicable[first_vehicle_in_epoch:last_vehicle_in_epoch + 1],
#         capacities_arcs=instance.capacities_arcs[:],
#         travel_times_arcs=instance.travel_times_arcs[:],
#         last_position_for_reconstruction=[None for _ in range(last_vehicle_in_epoch + 1 - first_vehicle_in_epoch)])


# def get_epoch_instances(global_instance: Instance, solver_params: SolverParameters) -> EpochInstances:
#     """
#     Create epoch instances from the global instance based on solver parameters.
#     """
#     last_vehicle_epochs = get_last_vehicle_for_each_epoch(
#         solver_params.epoch_size, global_instance.release_times
#     )
#     epoch_instances = []
#
#     first_vehicle_in_epoch = 0
#
#     for epoch_id, last_vehicle_in_epoch in enumerate(last_vehicle_epochs):
#         # Generate an epoch instance for the current epoch
#         epoch_instance = get_epoch_instance(
#             global_instance, epoch_id, first_vehicle_in_epoch, last_vehicle_in_epoch
#         )
#         epoch_instances.append(epoch_instance)
#
#         # Update the first vehicle for the next epoch
#         first_vehicle_in_epoch = last_vehicle_in_epoch + 1
#
#     return epoch_instances


def get_epoch_instance(
        instance: Instance,
        epoch_id: int,
        solver_params: SolverParameters,
        trips_from_previous_epoch: Optional[list[int]] = None
) -> EpochInstance:
    """Creates an EpochInstance for the specified epoch_id."""
    first_time_epoch = epoch_id * solver_params.epoch_size * 60
    last_time_epoch = (epoch_id + 1) * solver_params.epoch_size * 60 - TOLERANCE

    # Determine the first and last trips in the epoch based on their start times
    first_trip_in_epoch = next(
        (idx for idx, start_time in enumerate(instance.release_times) if start_time >= first_time_epoch),
        None
    )
    last_trip_in_epoch = next(
        (idx for idx, start_time in enumerate(instance.release_times) if start_time > last_time_epoch),
        len(instance.release_times) - 1
    ) - 1

    # Combine trip IDs from the previous epoch and current epoch
    trip_ids_in_epoch = sorted(
        (trips_from_previous_epoch or []) +
        list(range(first_trip_in_epoch, last_trip_in_epoch + 1))
    )

    # Generate the EpochInstance
    return EpochInstance(
        epoch_id=epoch_id,
        instance=instance,
        trip_original_ids=trip_ids_in_epoch,
        trip_ids_from_previous_epoch=trips_from_previous_epoch,
        last_position_for_reconstruction=[None for _ in trip_ids_in_epoch]
    )
