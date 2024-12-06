from __future__ import annotations

import os
import typing
from dataclasses import dataclass, field

from utils.classes import CompleteSolution
from input_data import InputData, SAVE_CPP_INSTANCE
from utils.aliases import *
from utils.aliases import Time, Staggering

path_to_cpp_instance = os.path.join(os.path.dirname(__file__),
                                    "../../cpp_module/catch2_tests/instancesForTest/instanceForLocalSearch")


def save_list_of_strings_file(listOfValues: list[typing.Any], fileName: str, path: str):
    with open(f"{path}/{fileName}.txt", "w") as outfile:
        for i, value in enumerate(listOfValues):
            if i < len(listOfValues) - 1:
                outfile.write(str(value) + "\n")
            else:
                outfile.write(str(value))


@dataclass
class Instance:
    input_data: InputData
    osm_info_arcs_utilized: list[dict[str:typing.Any]]
    capacities_arcs: list[int]
    release_times_dataset: list[float]
    arrival_times_dataset: list[float]
    trip_routes: list[list[int]]
    travel_times_arcs: list[float]
    clock_start_epoch: int = 0
    due_dates: list[float] = field(default_factory=list[float])
    undivided_conflicting_sets: list[list[list[int]]] = field(default_factory=list[list[list[int]]])
    conflicting_sets: list[list[int]] = field(default_factory=list[list[int]])
    latest_departure_times: list[list[float]] = field(default_factory=list[list[float]])
    earliest_departure_times: list[list[float]] = field(default_factory=list[list[float]])
    min_delay_on_arc: list[list[float]] = field(default_factory=list[list[float]])
    max_delay_on_arc: list[list[float]] = field(default_factory=list[list[float]])
    start_solution_time: float = 0
    removed_vehicles: list[int] = field(default_factory=list[int])
    deadlines: Optional[list[Time]] = None
    max_staggering_applicable: Optional[list[Staggering]] = None

    def get_lb_travel_time(self) -> float:
        """Return sum of the free flow times of the routes of trips contained in instance"""
        return sum([self.travel_times_arcs[arc] for path in self.trip_routes for arc in path])

    def set_deadlines(self, deadlines: list[Time]):
        """Create list of the latest arrival time at destination for trips.
        It is assumed to be the arrival time at the destination plus a delta
        inputData.deadlineFactor: value comprised between 0 and 100, denotes percentage of status quo
        travel time to use to extend the deadline
        :return list of deadlines
        """
        if self.deadlines is None:
            self.deadlines = deadlines
            print(f"Deadline delta is {self.input_data.deadline_factor} % of congested travel time")
        else:
            raise ValueError("trying to override deadlines with class method!")

    def set_max_staggering_applicable(self):
        """
        Compute for each trip the maximum applicable staggering time.

        Returns:
        A list of maximum staggering times for each vehicle.
        """

        if self.deadlines is None:
            raise ValueError("trying to access empty deadlines")

        if self.max_staggering_applicable is not None:
            raise ValueError("trying to override maxStaggeringApplicable with class method")

        # Initialize an empty list to store maximum staggering times for each vehicle
        max_staggering_times = []

        # Iterate over each vehicle and its corresponding path
        for vehicle, path in enumerate(self.trip_routes):
            # Calculate the total nominal travel time for the current path
            total_travel_time = sum(self.travel_times_arcs[arc] for arc in path)

            # Calculate staggering time based on staggering cap percentage
            if self.input_data.staggering_applicable_method == "fixed":
                staggering_cap_time = self.input_data.staggering_cap * 60
            elif self.input_data.staggering_applicable_method == "proportional":
                staggering_cap_time = self.input_data.staggering_cap / 100 * total_travel_time
            else:
                raise RuntimeError("wrong staggering applicable method specified!")

            # Calculate the maximum time available before the deadline, after accounting for release time
            time_until_deadline = self.deadlines[vehicle] - (total_travel_time + self.release_times_dataset[vehicle])

            # Determine the minimum of staggering cap time and time until deadline
            max_stagger_time = min(staggering_cap_time, time_until_deadline)

            # Append the calculated staggering time to the list
            max_staggering_times.append(max_stagger_time)

        self.max_staggering_applicable = max_staggering_times

    def check_optional_fields(self):
        if self.deadlines is None:
            raise ValueError("deadlines are none")
        if self.max_staggering_applicable is None:
            raise ValueError("max staggering applicable is none")


def _write_arc_based_shortest_paths_for_cpp_code(instance: Instance):
    with open(f"{path_to_cpp_instance}/arcBasedShortestPaths.txt", "w") as outfile:
        for vehiclePath in instance.trip_routes:
            outfile.writelines([str(arc) + "," for arc in vehiclePath if arc != 0])
            outfile.write("0")
            outfile.writelines("\n")


def _write_earliest_departure_times_for_cpp_code(instance: Instance):
    with open(f"{path_to_cpp_instance}/earliestDepartureTimes.txt", "w") as outfile:
        for vehicleEDs in instance.earliest_departure_times:
            outfile.writelines([str(ED) + "," for ED in vehicleEDs])
            outfile.writelines("\n")


def _write_latest_departure_times_for_cpp_code(instance: Instance):
    with open(f"{path_to_cpp_instance}/latestDepartureTimes.txt", "w") as outfile:
        for vehicleLDs in instance.latest_departure_times:
            outfile.writelines([str(LD) + "," for LD in vehicleLDs])
            outfile.writelines("\n")


def _write_conflicting_sets_after_preprocessing_for_cpp_code(instance: Instance):
    with open(f"{path_to_cpp_instance}/conflictingSets.txt", "w") as outfile:
        for conflictingSet in instance.conflicting_sets:
            if conflictingSet:
                outfile.writelines(
                    [str(vehicle) + "," for i, vehicle in enumerate(conflictingSet) if i < len(conflictingSet) - 1])
                outfile.write(str(conflictingSet[-1]) + ",\n")
            else:
                outfile.write("-1,\n")


def save_instance_for_testing_cpp_code(instance: Instance, statusQuo: CompleteSolution) -> None:
    if SAVE_CPP_INSTANCE:
        if not os.path.exists(path_to_cpp_instance):
            os.mkdir(path_to_cpp_instance)
        parameters = [instance.input_data.algorithm_time_limit]
        _write_arc_based_shortest_paths_for_cpp_code(instance)
        _write_earliest_departure_times_for_cpp_code(instance)
        _write_latest_departure_times_for_cpp_code(instance)
        _write_conflicting_sets_after_preprocessing_for_cpp_code(instance)
        save_list_of_strings_file(parameters, "parameters", path_to_cpp_instance)
        save_list_of_strings_file(instance.deadlines, "deadlines", path_to_cpp_instance)
        save_list_of_strings_file(instance.input_data.list_of_slopes, "list_of_slopes", path_to_cpp_instance)
        save_list_of_strings_file(instance.input_data.list_of_thresholds, "list_of_thresholds", path_to_cpp_instance)
        save_list_of_strings_file(instance.deadlines, "dueDates", path_to_cpp_instance)
        save_list_of_strings_file(instance.travel_times_arcs, "travelTimesArcsUtilized", path_to_cpp_instance)
        save_list_of_strings_file(instance.capacities_arcs, "nominalCapacitiesArcsUtilized",
                                  path_to_cpp_instance)
        save_list_of_strings_file(statusQuo.release_times, "releaseTimes", path_to_cpp_instance)
        save_list_of_strings_file(statusQuo.staggering_applicable, "remainingSlack", path_to_cpp_instance)


def print_total_free_flow_time(instance: Instance):
    totalFreeFlowTime = sum(
        [instance.travel_times_arcs[arc] for path in instance.trip_routes for arc in path])
    print(f"Total free flow time instance: {round(totalFreeFlowTime / 3600, 2)} [h]")


def get_instance(inputData: InputData,
                 arcBasedShortestPaths: list[NodesPath],
                 arcsFeatures,
                 releaseTimesDataset: list[Time],
                 arrivalTimesDataset: list[Time]):
    return Instance(
        osm_info_arcs_utilized=arcsFeatures.osm_info_arcs,
        trip_routes=arcBasedShortestPaths,
        travel_times_arcs=arcsFeatures.travel_times_arcs,
        capacities_arcs=arcsFeatures.capacities_arcs,
        input_data=inputData,
        release_times_dataset=releaseTimesDataset,
        arrival_times_dataset=arrivalTimesDataset
    )
