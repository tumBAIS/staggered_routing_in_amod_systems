from __future__ import annotations

import copy
import datetime
import itertools
from collections import namedtuple

import conflictingSetModule.split
from utils.aliases import VehicleSchedules, UndividedConflictingSets
from instanceModule.instance import Instance
from instanceModule.epochInstance import EpochInstance
from queue import PriorityQueue
from inputData import ACTIVATE_ASSERTIONS
from typing import Callable
from inputData import MIN_SET_CAPACITY

TimeBound = namedtuple("TimeBound",
                       ["arc", "earliestDeparture", "latestDeparture", "earliestArrival", "latestArrival",
                        "minDelayOnArc",
                        "maxDelayOnArc", "vehicle"])


def _splitTimeBoundsOnArcs(instance: Instance,
                           timeBoundsOnArcs: list[list[TimeBound]]) -> list[
    list[list[TimeBound]]]:
    boundsOnArcsSplit = [[] for _ in instance.travelTimesArcsUtilized]
    for arc, timeBounds in enumerate(timeBoundsOnArcs[1:], start=1):  # start enumeration from 1
        maximumLatestArrival = float('-inf')
        boundsSplit = []
        for vehicleBounds in sorted(timeBounds, key=lambda x: x.earliestDeparture):
            if vehicleBounds.earliestDeparture >= maximumLatestArrival:
                boundsOnArcsSplit[arc].append(boundsSplit) if boundsSplit else None
                boundsSplit = []
            boundsSplit.append(vehicleBounds)
            maximumLatestArrival = max(maximumLatestArrival, vehicleBounds.latestArrival)
        boundsOnArcsSplit[arc].append(boundsSplit) if boundsSplit else None

    return boundsOnArcsSplit


def _getUndividedConflictingSets(instance: Instance,
                                 boundsOnArcsSplit: list[list[list[TimeBound]]]) -> UndividedConflictingSets:
    undividedConflictingSets = [[[timeBound.vehicle for timeBound in boundsSet] if
                                 len(boundsSet) > max(MIN_SET_CAPACITY, instance.nominalCapacitiesArcs[
                                     arc] * instance.inputData.list_of_thresholds[0]) else [] for
                                 boundsSet in boundsOnArc
                                 ] if arc > 0 else [] for arc, boundsOnArc in enumerate(boundsOnArcsSplit)
                                ]

    return undividedConflictingSets


def _arrangeBoundsByVehicle(arcBasedTimeBounds: list[list[TimeBound]], paths: list[list[int]]):
    vehicleBasedTimeBounds: list[list[TimeBound]] = [[] for _ in paths]

    for arc, arcTimeBounds in enumerate(arcBasedTimeBounds):
        for bound in arcTimeBounds:
            vehicleBasedTimeBounds[bound.vehicle].append(bound)
    vehicleBasedTimeBounds = [sorted(vehicleBounds, key=lambda x: x.earliestDeparture) for vehicleBounds in
                              vehicleBasedTimeBounds]

    return vehicleBasedTimeBounds


def _getMaxDelayOnArcs(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.maxDelayOnArc for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def _getMinDelayOnArcs(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.minDelayOnArc for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def _getEarliestDepartureTimes(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.earliestDeparture for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def _getLatestDepartureTimes(vehicleBasedTimeBounds: list[list[TimeBound]]) -> list[list[float]]:
    return [
        [bound.latestDeparture for bound in sorted(boundsOfOneVehicle, key=lambda x: x.earliestDeparture)]
        for boundsOfOneVehicle in vehicleBasedTimeBounds
    ]


def _computeDelayOnArc(arc: int, instance: Instance, vehiclesOnArc: int) -> float:
    """Compute delay on arc according to an n-pieces latency function"""

    if arc == 0:
        return 0
    delay_at_pieces = [0]
    height_prev_piece = 0
    for i in range(len(instance.inputData.list_of_slopes)):
        th_capacity = instance.inputData.list_of_thresholds[i] * instance.nominalCapacitiesArcs[arc]
        slope = instance.travelTimesArcsUtilized[arc] * instance.inputData.list_of_slopes[i] / \
                instance.nominalCapacitiesArcs[arc]
        if vehiclesOnArc > th_capacity:
            delay_current_piece = height_prev_piece + slope * (vehiclesOnArc - th_capacity)
            delay_at_pieces.append(delay_current_piece)
        if i < len(instance.inputData.list_of_slopes) - 1:
            next_th_cap = instance.inputData.list_of_thresholds[i + 1] * instance.nominalCapacitiesArcs[arc]
            height_prev_piece += slope * (next_th_cap - th_capacity)
    return max(delay_at_pieces)


EarliestDeparture = namedtuple("EarliestDeparture", ["time", "arc", "vehicle", "position"])


def getEarliestDeparturesListAndPQ(freeFlowSchedule: VehicleSchedules, instance: Instance) -> \
        (list[list[EarliestDeparture]], PriorityQueue):
    earliestDeparturesPriorityQueue = PriorityQueue()
    arcBasedEarliestDepartures = [[] for _ in instance.travelTimesArcsUtilized]
    for vehicle, schedule in enumerate(freeFlowSchedule):
        firstArc = instance.arcBasedShortestPaths[vehicle][0]
        firstDeparture = EarliestDeparture(time=schedule[0], arc=firstArc, vehicle=vehicle, position=0)
        earliestDeparturesPriorityQueue.put(firstDeparture)
        for position, time in enumerate(schedule):
            arc = instance.arcBasedShortestPaths[vehicle][position]
            departure = EarliestDeparture(time=time, arc=arc, vehicle=vehicle, position=position)
            arcBasedEarliestDepartures[arc].append(departure)
    arcBasedEarliestDepartures = [sorted(x, key=lambda x: x.time) for x in arcBasedEarliestDepartures]
    return arcBasedEarliestDepartures, earliestDeparturesPriorityQueue


Arrival = namedtuple("Arrival", ["latest", "earliest", "latestDeparture"])


def _getConflictingLatestArrivals(arcBasedArrivals: list[list[Arrival]],
                                  earliestDeparture: EarliestDeparture) -> list[Arrival]:
    return [arrival for arrival in arcBasedArrivals[earliestDeparture.arc] if
            arrival.latest > earliestDeparture.time]


KnownBoundDeparture = namedtuple("KnownBoundDeparture", ["latest", "earliest", "latestArrival"])


def _getConflictingDepartures(allEarliestDepartures: list[list[EarliestDeparture]],
                              currentEarliestDeparture: EarliestDeparture,
                              currentLatestDeparture: float,
                              instance: Instance,
                              arcBasedTimeBounds: list[list[TimeBound]],
                              knownLatestArrivalTimes: list[list[float]]) -> list[KnownBoundDeparture]:
    conflictingDepartures = []
    for otherEarliestDeparture in allEarliestDepartures[currentEarliestDeparture.arc]:
        if otherEarliestDeparture.vehicle == currentEarliestDeparture.vehicle:
            continue
        isPotentialConflict = currentEarliestDeparture.time <= otherEarliestDeparture.time <= currentLatestDeparture
        if isPotentialConflict:
            otherPosition = instance.arcBasedShortestPaths[otherEarliestDeparture.vehicle].index(
                otherEarliestDeparture.arc)
            otherPreviousArc = instance.arcBasedShortestPaths[otherEarliestDeparture.vehicle][otherPosition - 1]
            otherPreviousTimeBound = next(
                (timeBound for timeBound in arcBasedTimeBounds[otherPreviousArc] if
                 timeBound.vehicle == otherEarliestDeparture.vehicle),
                None)
            otherLatestDepartureTime = otherPreviousTimeBound.latestArrival \
                if otherPreviousTimeBound is not None else float("inf")
            otherLatestArrivalOnThisArc = knownLatestArrivalTimes[otherEarliestDeparture.vehicle][
                otherPosition]
            conflictingDepartures.append(
                KnownBoundDeparture(earliest=otherEarliestDeparture.time, latest=otherLatestDepartureTime,
                                    latestArrival=otherLatestArrivalOnThisArc))
    return conflictingDepartures


def _combineConflicts(conflictingArrivals: list[Arrival],
                      conflcitingDepartures: list[KnownBoundDeparture]) -> list[tuple[float, str]]:
    """
    Combine conflicting latest arrivals and earliest departures into a sorted list of tuples.

    Args:
        conflictingArrivals (List[float]): List of conflicting latest arrivals.
        conflcitingDepartures (List[float]): List of conflicting earliest departures.

    Returns: List[Tuple[float, str]]: Sorted list of tuples (time, type), where type 'a' represents arrival and 'd'
    represents departure.
    """
    arrivals = [(arrival.latest, 'a') for arrival in conflictingArrivals]
    departures = [(departure.earliest, 'd') for departure in conflcitingDepartures]
    latest_arrivals = [(departure.latestArrival, 'a') for departure in conflcitingDepartures]

    listOfTuples = arrivals + departures + latest_arrivals
    sortedList = sorted(listOfTuples, key=lambda x: x[0])
    return sortedList


def _propagateMinDelay(earliestDepartures: list[list[EarliestDeparture]], minDelayOnThisArc: float,
                       departure: EarliestDeparture, instance: Instance) -> None:
    """
    Propagate the minimum delay on this arc to the earliest departures in the subsequent arcs in the path.

    Raises:
        RuntimeError: If the vehicle is not found in the subsequent arcs.
    """
    if minDelayOnThisArc < 1e-6:
        return

    if departure.arc == 0:
        # No need to propagate delay for the last arc
        return
    path = instance.arcBasedShortestPaths[departure.vehicle]
    currentPosition = path.index(departure.arc)

    # Collect the indices of departures for the subsequent arcs
    indicesDeparturesNextArcs = {
        arc: next(
            id_ED for id_ED, ED in enumerate(earliestDepartures[arc]) if departure.vehicle == ED.vehicle)
        for arc in path[currentPosition + 1:]
    }

    for arc in indicesDeparturesNextArcs:
        try:
            # Find the first index of departure for the vehicle in the arc
            index = indicesDeparturesNextArcs[arc]
            newTime = earliestDepartures[arc][index].time + minDelayOnThisArc
            # Update the departure time with the propagated delay
            earliestDepartures[arc][index] = earliestDepartures[arc][index]._replace(time=newTime)
        except StopIteration:
            raise RuntimeError("Vehicle not found in the subsequent arcs!")


def _assertTimeBound(timeBound: TimeBound, instance: Instance, earliestDeparture: EarliestDeparture) -> None:
    if ACTIVATE_ASSERTIONS:
        assert (
                timeBound.latestArrival - timeBound.earliestArrival > -1e-6), \
            f"TimeBoundError#1: -> Latest arrival {timeBound.latestArrival} > " \
            f"earliest arrival {timeBound.earliestArrival} \n" \
            f"time bound: {timeBound}, travel time arc: {instance.travelTimesArcsUtilized[earliestDeparture.arc]} " \
            f"departure: {earliestDeparture} "
        assert (
                timeBound.latestDeparture - timeBound.earliestDeparture > -1e-6), \
            f"TimeBoundError#2: {timeBound} -> Latest departure > earliest departure"


def _getLatestDeparture(earliestDeparture: EarliestDeparture, instance: Instance, arcBasedTimeBounds) -> float:
    if earliestDeparture.position == 0:
        # First arc
        latestDeparture = earliestDeparture.time + instance.maxStaggeringApplicable[earliestDeparture.vehicle]
    else:
        previousArc = instance.arcBasedShortestPaths[earliestDeparture.vehicle][earliestDeparture.position - 1]
        isPreviousDeparture: Callable[[TimeBound], bool] = lambda x: x.vehicle == earliestDeparture.vehicle
        latestDeparture = next(
            (bound.latestArrival for bound in arcBasedTimeBounds[previousArc] if isPreviousDeparture(bound)), None)

    return latestDeparture


def _getEarliestArrivalTime(conflictingArrivals: list[Arrival], currentLatestDeparture: float,
                            instance: Instance, earliestDeparture: EarliestDeparture) -> tuple[float, float]:
    arc_threshold_capacity = max(MIN_SET_CAPACITY, instance.nominalCapacitiesArcs[
        earliestDeparture.arc] * instance.inputData.list_of_thresholds[0])
    min_vehicles_on_arc = sum(1 for arrival in conflictingArrivals if
                              arrival.latestDeparture < earliestDeparture.time and
                              currentLatestDeparture < arrival.earliest) + 1
    min_delay = _computeDelayOnArc(earliestDeparture.arc, instance,
                                   min_vehicles_on_arc) if min_vehicles_on_arc > arc_threshold_capacity else 0
    earliest_arrival_time = earliestDeparture.time + min_delay + instance.travelTimesArcsUtilized[earliestDeparture.arc]
    return earliest_arrival_time, min_delay


def _getLatestArrivalTime(conflictingArrivals: list[Arrival],
                          conflictingEarliestDepartures: list[KnownBoundDeparture],
                          earliestDeparture: EarliestDeparture, latestDepartureTime: float,
                          instance: Instance,
                          knownLatestArrivalTimes: list[list[float]]) -> tuple[float, float]:
    knownLatestArrival = knownLatestArrivalTimes[earliestDeparture.vehicle][earliestDeparture.position]
    nominalTT = instance.travelTimesArcsUtilized[earliestDeparture.arc]
    maxDelay = 0.0
    sortedPotentialConflictTimes = _combineConflicts(conflictingArrivals, conflictingEarliestDepartures)

    currentLatestArrival = latestDepartureTime + instance.travelTimesArcsUtilized[earliestDeparture.arc]
    if not sortedPotentialConflictTimes:
        latestArrival = min(knownLatestArrival, currentLatestArrival)
        return latestArrival, 0
    vehiclesOnArc = len(conflictingArrivals) + 1
    sortedPotentialConflictTimes = [item for item in sortedPotentialConflictTimes if
                                    not (item[1] == "a" and item[0] > latestDepartureTime)]
    sortedPotentialConflictTimes.append((latestDepartureTime, "latest_departure"))
    for intervalEnd, eventType in sortedPotentialConflictTimes:
        delay = _computeDelayOnArc(earliestDeparture.arc, instance, vehiclesOnArc)
        latestArrival = intervalEnd + delay + nominalTT
        if latestArrival > currentLatestArrival:
            currentLatestArrival = copy.copy(latestArrival)
        if delay > maxDelay:
            maxDelay = copy.copy(delay)
        vehiclesOnArc += 1 if eventType == "d" else (-1 if eventType == "a" else 0)

    return min(knownLatestArrival, currentLatestArrival), maxDelay


def _getArcBasedTimeBounds(instance: Instance,
                           knownLatestArrivalTimes: list[list[float]],
                           freeFlowSchedule: VehicleSchedules) -> list[list[TimeBound]]:
    # Initialize data structures
    arcBasedArrivals: list[list[Arrival]] = [[] for _ in instance.travelTimesArcsUtilized]
    arcBasedTimeBounds: list[list[TimeBound]] = [[] for _ in instance.travelTimesArcsUtilized]
    arcBasedEarliestDepartures, EDPQ = getEarliestDeparturesListAndPQ(freeFlowSchedule, instance)
    while not EDPQ.empty():
        # Get info departure
        earliestDeparture = EDPQ.get()
        latestDeparture = _getLatestDeparture(earliestDeparture, instance, arcBasedTimeBounds)

        # Find conflicting latest arrivals and earliest departures
        conflictingArrivals = _getConflictingLatestArrivals(arcBasedArrivals, earliestDeparture)
        conflictingEarliestDepartures = _getConflictingDepartures(arcBasedEarliestDepartures,
                                                                  earliestDeparture,
                                                                  latestDeparture, instance,
                                                                  arcBasedTimeBounds,
                                                                  knownLatestArrivalTimes)

        earliestArrival, minDelayOnArc = _getEarliestArrivalTime(conflictingArrivals,
                                                                 latestDeparture, instance,
                                                                 earliestDeparture)
        _propagateMinDelay(arcBasedEarliestDepartures, minDelayOnArc, earliestDeparture, instance)
        latestArrival, maxDelayOnArc = \
            _getLatestArrivalTime(conflictingArrivals,
                                  conflictingEarliestDepartures,
                                  earliestDeparture, latestDeparture,
                                  instance, knownLatestArrivalTimes)

        arcBasedArrivals[earliestDeparture.arc].append(
            Arrival(earliest=earliestArrival, latest=latestArrival, latestDeparture=latestDeparture))

        # Create a time bound object
        timeBound = TimeBound(
            arc=earliestDeparture.arc,
            vehicle=earliestDeparture.vehicle,
            earliestDeparture=earliestDeparture.time,
            latestDeparture=latestDeparture,
            earliestArrival=earliestArrival,
            latestArrival=latestArrival,
            minDelayOnArc=minDelayOnArc,
            maxDelayOnArc=maxDelayOnArc
        )
        # Validate the time bound
        _assertTimeBound(timeBound, instance, earliestDeparture)

        # Append the time bound to the corresponding arc
        arcBasedTimeBounds[earliestDeparture.arc].append(timeBound)
        vehicleIsTraveling = instance.arcBasedShortestPaths[earliestDeparture.vehicle][earliestDeparture.position] != 0
        if vehicleIsTraveling:
            nextArc = instance.arcBasedShortestPaths[earliestDeparture.vehicle][earliestDeparture.position + 1]
            nextEarliestDeparture = EarliestDeparture(time=earliestArrival,
                                                      arc=nextArc,
                                                      vehicle=earliestDeparture.vehicle,
                                                      position=earliestDeparture.position + 1)
            EDPQ.put(nextEarliestDeparture)
    # Sort the time bounds on each arc based on earliest departure time
    arcBasedTimeBounds = [sorted(timeBoundsOnArc, key=lambda x: x.earliestDeparture) for timeBoundsOnArc in
                          arcBasedTimeBounds]

    return arcBasedTimeBounds


def _getInitialLatestArrivalTimes(instance, ffSchedule):
    assert len(instance.deadlines) == len(ffSchedule)
    assert all(deadline + 1e-4 >= schedule[-1] for deadline, schedule in zip(instance.deadlines, ffSchedule))
    return [[schedule[position + 1] + instance.deadlines[vehicle] - schedule[-1] for position, _ in
             enumerate(schedule[:-1])] + [
                instance.deadlines[vehicle]]
            for vehicle, schedule in enumerate(ffSchedule)
            ]


def get_bounds_vehicle(instance, vehicle, arc):
    path = instance.arcBasedShortestPaths[vehicle]
    index_arc = path.index(arc)
    next_arx = instance.arcBasedShortestPaths[vehicle][index_arc + 1]
    earliest_entry = instance.earliestDepartureTimes[vehicle][index_arc]
    latest_entry = instance.latestDepartureTimes[vehicle][index_arc]
    earliest_leave = instance.earliestDepartureTimes[vehicle][index_arc + 1]
    latest_leave = instance.latestDepartureTimes[vehicle][index_arc + 1]
    return earliest_entry, latest_entry, earliest_leave, latest_leave


def estimate_big_m_necessary(instance) -> int:
    print("estimating big-m...", end=" ")
    necessary_big_m = 0

    for arc, conf_set in enumerate(instance.conflictingSets):
        for vehicle_1, vehicle_2 in itertools.permutations(conf_set, 2):
            constraints_to_add = 6
            e_e_1, e_l_1, l_e_1, l_l_1 = get_bounds_vehicle(instance, vehicle_1, arc)
            e_e_2, e_l_2, l_e_2, l_l_2 = get_bounds_vehicle(instance, vehicle_2, arc)
            alpha_must_be_one = e_l_2 < e_e_1
            beta_must_be_one = e_l_1 < l_e_2
            gamma_must_be_one = alpha_must_be_one and beta_must_be_one
            alpha_must_be_zero = e_l_1 < e_e_2
            beta_must_be_zero = l_l_2 < e_e_1
            if alpha_must_be_one:
                constraints_to_add -= 2
            if beta_must_be_one:
                constraints_to_add -= 2
            if gamma_must_be_one:
                constraints_to_add -= 2
            if alpha_must_be_zero or beta_must_be_zero:
                constraints_to_add = 0

            necessary_big_m += constraints_to_add

    print(f"necessary {necessary_big_m} big-m constraints")
    return necessary_big_m


def addConflictingSetsToInstance(
        instance: Instance | EpochInstance,
        ffSchedule: VehicleSchedules) -> None:
    print("Adding undivided conflicting sets to instanceModule...", end=" ")
    clock_start = datetime.datetime.now().timestamp()
    knownLatestArrivalTimes = _getInitialLatestArrivalTimes(instance, ffSchedule)
    while True:
        arcBasedTimeBounds = _getArcBasedTimeBounds(instance, knownLatestArrivalTimes, ffSchedule)
        boundsOnArcsSplit = _splitTimeBoundsOnArcs(instance, arcBasedTimeBounds)
        vehicleBasedTimeBounds = _arrangeBoundsByVehicle(arcBasedTimeBounds, instance.arcBasedShortestPaths)
        newLatestArrivalTimes = [[bound.latestArrival for bound in bounds] for bounds in vehicleBasedTimeBounds]
        if knownLatestArrivalTimes == newLatestArrivalTimes:
            break
        knownLatestArrivalTimes = newLatestArrivalTimes[:]

    instance.undividedConflictingSets = _getUndividedConflictingSets(instance, boundsOnArcsSplit)
    instance.earliestDepartureTimes = _getEarliestDepartureTimes(vehicleBasedTimeBounds)
    instance.latestDepartureTimes = _getLatestDepartureTimes(vehicleBasedTimeBounds)
    instance.minDelayOnArc = _getMinDelayOnArcs(vehicleBasedTimeBounds)
    instance.maxDelayOnArc = _getMaxDelayOnArcs(vehicleBasedTimeBounds)

    conflictingSetModule.split.splitConflictingSets(instance)
    clock_end = datetime.datetime.now().timestamp()
    print(f"done! - time necessary: {clock_end - clock_start:.2f} [s]")

    return
