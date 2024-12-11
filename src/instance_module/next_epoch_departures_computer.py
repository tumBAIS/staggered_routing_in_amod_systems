from __future__ import annotations

import copy
from collections import namedtuple
from enum import Enum

from input_data import SolverParameters
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution


class NextEpochDeparturesComputer:
    """
    Class responsible for computing and updating departures for the next epoch
    based on current epoch conditions and conflicts.
    """

    def __init__(self):
        self.change_made = True
        self.departures_to_modify: list[NextEpochDeparture] = []
        self.departures_to_add: list[NextEpochDeparture] = []
        self.vehicles_to_check: set[int] = set()
        self.indices_departures_to_modify: list[int] = []

    def run(self, next_epoch_departures: list[NextEpochDeparture],
            current_epoch_instance: EpochInstance,
            current_epoch_status_quo: EpochSolution,
            vehicle_status_list: list[VehicleStatus],
            solver_params: SolverParameters) -> list[NextEpochDeparture]:
        """
        Main method to update departures for the next epoch.
        """
        self._reset_attributes()
        for first_departure in next_epoch_departures:
            if first_departure.vehicle not in self.vehicles_to_check:
                continue
            self.vehicles_to_check.remove(first_departure.vehicle)
            following_departure = copy.deepcopy(first_departure)

            while _is_time_in_current_epoch(following_departure, current_epoch_instance, solver_params):
                self._activate_other_conflicting_vehicles(
                    current_epoch_status_quo,
                    following_departure,
                    current_epoch_instance,
                    vehicle_status_list,
                    next_epoch_departures
                )
                if _is_current_vehicle_in_system(following_departure, current_epoch_instance):
                    following_departure = _get_following_next_epoch_departure(
                        current_epoch_status_quo, current_epoch_instance, following_departure
                    )
                else:
                    break  # Vehicle has left the system

        self._apply_changes_to_next_epoch_departures(vehicle_status_list, next_epoch_departures)
        return next_epoch_departures

    def _apply_changes_to_next_epoch_departures(self, vehicle_status_list, next_epoch_departures):
        """
        Apply all modifications and additions to the list of next epoch departures.
        """
        for index, departure_to_modify in zip(self.indices_departures_to_modify, self.departures_to_modify):
            next_epoch_departures[index] = departure_to_modify

        next_epoch_departures.extend(self.departures_to_add)
        for departure_to_add in self.departures_to_add:
            vehicle_status_list[departure_to_add.vehicle] = VehicleStatus.ACTIVE

    def _update_next_epoch_departure_to_add(self, other_vehicle_info: OtherVehicleInfo, current_vehicle) -> None:
        """
        Add or update a departure for the next epoch.
        """
        index_departure, stored_departure = _get_stored_next_epoch_departure(
            self.departures_to_add, other_vehicle_info.vehicle
        )
        if index_departure is None:
            # Add a new departure
            self.departures_to_add.append(
                NextEpochDeparture(
                    vehicle=other_vehicle_info.vehicle,
                    position=other_vehicle_info.position,
                    time=other_vehicle_info.departure_time,
                    arc=other_vehicle_info.arc
                )
            )
            self.change_made = True
            self.vehicles_to_check.update({other_vehicle_info.vehicle, current_vehicle})
        else:
            # Update existing departure if the new one is earlier
            if other_vehicle_info.departure_time < stored_departure.time:
                self.departures_to_add[index_departure] = NextEpochDeparture(
                    vehicle=other_vehicle_info.vehicle,
                    position=other_vehicle_info.position,
                    time=other_vehicle_info.departure_time,
                    arc=other_vehicle_info.arc
                )
                self.change_made = True
                self.vehicles_to_check.update({other_vehicle_info.vehicle, current_vehicle})

    def _update_next_epoch_departure_to_modify(self, active_departures: list[NextEpochDeparture],
                                               other_vehicle_info: OtherVehicleInfo, current_vehicle: int):
        """
        Modify an existing departure for the next epoch.
        """
        index_departure, stored_departure = _get_stored_next_epoch_departure(
            active_departures, other_vehicle_info.vehicle
        )

        if other_vehicle_info.departure_time < stored_departure.time:
            if index_departure in self.indices_departures_to_modify:
                current_departure = self.departures_to_modify[
                    self.indices_departures_to_modify.index(index_departure)
                ]
                if other_vehicle_info.departure_time < current_departure.time:
                    self.departures_to_modify[
                        self.indices_departures_to_modify.index(index_departure)
                    ] = NextEpochDeparture(
                        vehicle=other_vehicle_info.vehicle,
                        position=other_vehicle_info.position,
                        time=other_vehicle_info.departure_time,
                        arc=other_vehicle_info.arc
                    )
                    self.change_made = True
                    self.vehicles_to_check.update({other_vehicle_info.vehicle, current_vehicle})
            else:
                self.indices_departures_to_modify.append(index_departure)
                self.departures_to_modify.append(
                    NextEpochDeparture(
                        vehicle=other_vehicle_info.vehicle,
                        position=other_vehicle_info.position,
                        time=other_vehicle_info.departure_time,
                        arc=other_vehicle_info.arc
                    )
                )
                self.change_made = True
                self.vehicles_to_check.update({other_vehicle_info.vehicle, current_vehicle})

    def _reset_attributes(self):
        """Reset all attributes to their initial state."""
        self.departures_to_modify = []
        self.departures_to_add = []
        self.indices_departures_to_modify = []
        self.change_made = False

    def initialize_vehicles_to_check(self, next_epoch_departures: list[NextEpochDeparture]):
        """Initialize the set of vehicles to check for conflicts."""
        self.vehicles_to_check = {departure.vehicle for departure in next_epoch_departures}

    def _activate_other_conflicting_vehicles(self, current_epoch_status_quo, following_departure,
                                             current_epoch_instance, vehicle_status_list, next_epoch_departures):
        """
        Activate other vehicles that are conflicting with the given departure.
        """
        other_vehicles_on_arc = [
            vehicle for vehicle in current_epoch_status_quo.vehicles_utilizing_arcs[following_departure.arc]
            if vehicle != following_departure.vehicle
        ]
        for other_vehicle in other_vehicles_on_arc:
            other_vehicle_info = _get_other_vehicle_info(
                current_epoch_instance, current_epoch_status_quo, other_vehicle, following_departure.arc
            )
            if _is_other_conflicting(other_vehicle_info, following_departure):
                if vehicle_status_list[other_vehicle] == VehicleStatus.INACTIVE:
                    self._update_next_epoch_departure_to_add(other_vehicle_info, following_departure.vehicle)
                elif vehicle_status_list[other_vehicle] == VehicleStatus.ACTIVE:
                    self._update_next_epoch_departure_to_modify(next_epoch_departures, other_vehicle_info,
                                                                following_departure.vehicle)


# Supporting namedtuples and helper functions

NextEpochDeparture = namedtuple("NextEpochDeparture", ["vehicle", "position", "time", "arc"])
OtherVehicleInfo = namedtuple("OtherVehicleInfo", ["departure_time", "arrival_time", "position", "vehicle", "arc"])


def _get_stored_next_epoch_departure(departures, vehicle) -> tuple[int, NextEpochDeparture]:
    """Retrieve an existing departure for a specific vehicle."""
    return next(
        ((i, departure) for i, departure in enumerate(departures) if _is_same_vehicle_departure(departure, vehicle)),
        (None, None)
    )


def _get_other_vehicle_info(current_epoch_instance: EpochInstance, current_epoch_status_quo: EpochSolution,
                            other_vehicle: int, arc: int) -> OtherVehicleInfo:
    """Get detailed information about another vehicle."""
    position = current_epoch_instance.trip_routes[other_vehicle].index(arc)
    departure_time = current_epoch_status_quo.congested_schedule[other_vehicle][position]
    arrival_time = current_epoch_status_quo.congested_schedule[other_vehicle][position + 1]
    return OtherVehicleInfo(
        departure_time=departure_time,
        arrival_time=arrival_time,
        position=position,
        vehicle=other_vehicle,
        arc=arc
    )


def _is_other_conflicting(other_vehicle_info, next_epoch_departure):
    """Check if another vehicle conflicts with the given departure."""
    return other_vehicle_info.departure_time <= next_epoch_departure.time < other_vehicle_info.arrival_time


def _is_time_in_current_epoch(next_epoch_departure, current_epoch_instance, solver_params: SolverParameters):
    """Check if a departure time falls within the current epoch."""
    return next_epoch_departure.time / 60 < (current_epoch_instance.epoch_id + 1) * solver_params.epoch_size


def _is_current_vehicle_in_system(next_epoch_departure, current_epoch_instance) -> bool:
    """Check if a vehicle is still in the system."""
    return next_epoch_departure.position < len(current_epoch_instance.trip_routes[next_epoch_departure.vehicle]) - 1


def _get_following_next_epoch_departure(current_epoch_status_quo, current_epoch_instance,
                                        next_epoch_departure) -> NextEpochDeparture:
    """Get the next departure for a vehicle in the current epoch."""
    next_time = current_epoch_status_quo.congested_schedule[next_epoch_departure.vehicle][
        next_epoch_departure.position + 1]
    next_arc = current_epoch_instance.trip_routes[next_epoch_departure.vehicle][next_epoch_departure.position + 1]
    return NextEpochDeparture(
        vehicle=next_epoch_departure.vehicle,
        position=next_epoch_departure.position + 1,
        time=next_time,
        arc=next_arc
    )


def _is_same_vehicle_departure(departure: NextEpochDeparture, vehicle: int) -> bool:
    """Check if a departure belongs to the given vehicle."""
    return departure.vehicle == vehicle


class VehicleStatus(Enum):
    ACTIVE = 1
    INACTIVE = 2
