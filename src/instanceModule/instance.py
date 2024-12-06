from __future__ import annotations

import os
import typing
from dataclasses import dataclass, field

from utils.classes import CompleteSolution
from inputData import InputData, SAVE_CPP_INSTANCE
from utils.aliases import *
from utils.aliases import Time, Staggering

pathToCppInstance = os.path.join(os.path.dirname(__file__),
                                 "../../cpp_module/catch2_tests/instancesForTest/instanceForLocalSearch")


def saveListOfStringsFile(listOfValues: list[typing.Any], fileName: str, path: str):
    with open(f"{path}/{fileName}.txt", "w") as outfile:
        for i, value in enumerate(listOfValues):
            if i < len(listOfValues) - 1:
                outfile.write(str(value) + "\n")
            else:
                outfile.write(str(value))


@dataclass
class Instance:
    inputData: InputData
    osmInfoArcsUtilized: list[dict[str:typing.Any]]
    capacities_arcs: list[int]
    releaseTimesDataset: list[float]
    arrivalTimesDataset: list[float]
    trip_routes: list[list[int]]
    travel_times_arcs: list[float]
    clockStartEpoch: int = 0
    dueDates: list[float] = field(default_factory=list[float])
    undividedConflictingSets: list[list[list[int]]] = field(default_factory=list[list[list[int]]])
    conflictingSets: list[list[int]] = field(default_factory=list[list[int]])
    latestDepartureTimes: list[list[float]] = field(default_factory=list[list[float]])
    earliestDepartureTimes: list[list[float]] = field(default_factory=list[list[float]])
    minDelayOnArc: list[list[float]] = field(default_factory=list[list[float]])
    maxDelayOnArc: list[list[float]] = field(default_factory=list[list[float]])
    startSolutionTime: float = 0
    removedVehicles: list[int] = field(default_factory=list[int])
    deadlines: Optional[list[Time]] = None
    maxStaggeringApplicable: Optional[list[Staggering]] = None

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
            print(f"Deadline delta is {self.inputData.deadline_factor} % of congested travel time")
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

        if self.maxStaggeringApplicable is not None:
            raise ValueError("trying to override maxStaggeringApplicable with class method")

        # Initialize an empty list to store maximum staggering times for each vehicle
        max_staggering_times = []

        # Iterate over each vehicle and its corresponding path
        for vehicle, path in enumerate(self.trip_routes):
            # Calculate the total nominal travel time for the current path
            total_travel_time = sum(self.travel_times_arcs[arc] for arc in path)

            # Calculate staggering time based on staggering cap percentage
            if self.inputData.staggeringApplicableMethod == "fixed":
                staggering_cap_time = self.inputData.staggering_cap * 60
            elif self.inputData.staggeringApplicableMethod == "proportional":
                staggering_cap_time = self.inputData.staggering_cap / 100 * total_travel_time
            else:
                raise RuntimeError("wrong staggering applicable method specified!")

            # Calculate the maximum time available before the deadline, after accounting for release time
            time_until_deadline = self.deadlines[vehicle] - (total_travel_time + self.releaseTimesDataset[vehicle])

            # Determine the minimum of staggering cap time and time until deadline
            max_stagger_time = min(staggering_cap_time, time_until_deadline)

            # Append the calculated staggering time to the list
            max_staggering_times.append(max_stagger_time)

        self.maxStaggeringApplicable = max_staggering_times

    def check_optional_fields(self):
        if self.deadlines is None:
            raise ValueError("deadlines are none")
        if self.maxStaggeringApplicable is None:
            raise ValueError("max staggering applicable is none")


def _writeArcBasedShortestPathsForCppCode(instance: Instance):
    with open(f"{pathToCppInstance}/arcBasedShortestPaths.txt", "w") as outfile:
        for vehiclePath in instance.trip_routes:
            outfile.writelines([str(arc) + "," for arc in vehiclePath if arc != 0])
            outfile.write("0")
            outfile.writelines("\n")


def _writeEarliestDepartureTimesForCppCode(instance: Instance):
    with open(f"{pathToCppInstance}/earliestDepartureTimes.txt", "w") as outfile:
        for vehicleEDs in instance.earliestDepartureTimes:
            outfile.writelines([str(ED) + "," for ED in vehicleEDs])
            outfile.writelines("\n")


def _writeLatestDepartureTimesForCppCode(instance: Instance):
    with open(f"{pathToCppInstance}/latestDepartureTimes.txt", "w") as outfile:
        for vehicleLDs in instance.latestDepartureTimes:
            outfile.writelines([str(LD) + "," for LD in vehicleLDs])
            outfile.writelines("\n")


def _writeConflictingSetsAfterPreprocessingForCppCode(instance: Instance):
    with open(f"{pathToCppInstance}/conflictingSets.txt", "w") as outfile:
        for conflictingSet in instance.conflictingSets:
            if conflictingSet:
                outfile.writelines(
                    [str(vehicle) + "," for i, vehicle in enumerate(conflictingSet) if i < len(conflictingSet) - 1])
                outfile.write(str(conflictingSet[-1]) + ",\n")
            else:
                outfile.write("-1,\n")


def saveInstanceForTestingCppCode(instance: Instance, statusQuo: CompleteSolution) -> None:
    if SAVE_CPP_INSTANCE:
        if not os.path.exists(pathToCppInstance):
            os.mkdir(pathToCppInstance)
        parameters = [instance.inputData.algorithmTimeLimit]
        _writeArcBasedShortestPathsForCppCode(instance)
        _writeEarliestDepartureTimesForCppCode(instance)
        _writeLatestDepartureTimesForCppCode(instance)
        _writeConflictingSetsAfterPreprocessingForCppCode(instance)
        saveListOfStringsFile(parameters, "parameters", pathToCppInstance)
        saveListOfStringsFile(instance.deadlines, "deadlines", pathToCppInstance)
        saveListOfStringsFile(instance.inputData.list_of_slopes, "list_of_slopes", pathToCppInstance)
        saveListOfStringsFile(instance.inputData.list_of_thresholds, "list_of_thresholds", pathToCppInstance)
        saveListOfStringsFile(instance.deadlines, "dueDates", pathToCppInstance)
        saveListOfStringsFile(instance.travel_times_arcs, "travelTimesArcsUtilized", pathToCppInstance)
        saveListOfStringsFile(instance.capacities_arcs, "nominalCapacitiesArcsUtilized",
                              pathToCppInstance)
        saveListOfStringsFile(statusQuo.releaseTimes, "releaseTimes", pathToCppInstance)
        saveListOfStringsFile(statusQuo.staggeringApplicable, "remainingSlack", pathToCppInstance)


def printTotalFreeFlowTime(instance: Instance):
    totalFreeFlowTime = sum(
        [instance.travel_times_arcs[arc] for path in instance.trip_routes for arc in path])
    print(f"Total free flow time instance: {round(totalFreeFlowTime / 3600, 2)} [h]")


def getInstance(inputData: InputData,
                arcBasedShortestPaths: list[NodesPath],
                arcsFeatures,
                releaseTimesDataset: list[Time],
                arrivalTimesDataset: list[Time]):
    return Instance(
        osmInfoArcsUtilized=arcsFeatures.osm_info_arcs,
        trip_routes=arcBasedShortestPaths,
        travel_times_arcs=arcsFeatures.travel_times_arcs,
        capacities_arcs=arcsFeatures.capacities_arcs,
        inputData=inputData,
        releaseTimesDataset=releaseTimesDataset,
        arrivalTimesDataset=arrivalTimesDataset
    )
