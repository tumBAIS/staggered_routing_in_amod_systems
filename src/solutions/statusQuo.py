import dataclasses
import datetime
import json
import os.path
import typing

import numpy as np

from congestionModel.conflictBinaries import getConflictBinaries, get_flow_from_binaries
from utils.prints import printInfoConflictingSetsSizes, \
    printInfoArcsUtilized, printInfoLengthTrips
from utils.classes import EpochSolution
from instanceModule.epochInstance import EpochInstance
from conflictingSetModule.undividedConflictingSets import addConflictingSetsToInstance, estimate_big_m_necessary
from congestionModel.core import getTotalTravelTime, getCongestedSchedule, getFreeFlowSchedule, \
    getDelaysOnArcs, getTotalDelay
from inputData import ACTIVATE_ASSERTIONS, MIN_SET_CAPACITY


def _getVehiclesUtilizingArcs(arcBasedShortestPaths: list[list[int]]) -> list[list[int]]:
    vehiclesUtilizingArcs = [[] for _ in range(max([max(path) for path in arcBasedShortestPaths]) + 1)]  # type: ignore
    for vehicle, path in enumerate(arcBasedShortestPaths):
        for arc in path[:-1]:
            vehiclesUtilizingArcs[arc].append(vehicle)

    return vehiclesUtilizingArcs


def _assertTripsAreNotDuplicated(epochInstance, vehiclesUtilizingArcs):
    if ACTIVATE_ASSERTIONS:
        assert sorted(list(set(epochInstance.vehiclesOriginalIDS))) == sorted(epochInstance.vehiclesOriginalIDS), \
            f"vehicles IDs repeat themselves"
    for arc, conflictingSet in enumerate(epochInstance.conflictingSets):
        if conflictingSet:
            assert sorted(list(set(conflictingSet))) == sorted(conflictingSet), \
                f"repetitions in conflicting set"
            assert sorted(list(set(vehiclesUtilizingArcs[arc]))) == sorted(vehiclesUtilizingArcs[arc]), \
                f"repetitions in conflicting set"


@dataclasses.dataclass
class StatusQuoMetrics:
    congestedSchedule: list[list[float]]
    freeFlowSchedule: list[list[float]]
    delaysOnArcs: list[list[float]]
    releaseTimes: list[float]
    totalDelay: float


def compute_vehicles_on_arc_from_delay(delay, instance, arc, first_capacity, second_capacity):
    second_slope = instance.travel_times_arcs[arc] * instance.inputData.slopeSecondLine / \
                   max(instance.capacities_arcs[arc], MIN_SET_CAPACITY)
    third_slope = instance.travel_times_arcs[arc] * instance.inputData.slopeThirdLine / \
                  max(instance.capacities_arcs[arc], MIN_SET_CAPACITY)

    height_third_piece = second_slope * (second_capacity - first_capacity)
    if delay <= second_slope * (second_capacity - first_capacity):
        # First segment logic
        if delay > 0:
            vehiclesOnArc = (delay / second_slope) + first_capacity
        else:
            # If delay is 0 or negative, it's a special case
            vehiclesOnArc = first_capacity
    else:
        # Second segment logic
        vehiclesOnArc = ((delay - height_third_piece) / third_slope) + second_capacity

    return vehiclesOnArc


def get_distribution_info(list_of_values: list[float]):
    if len(list_of_values) > 0:
        return {
            "count": len(list_of_values),
            "mean": round(float(np.mean(list_of_values)), 2),
            "25_percentile": round(float(np.percentile(list_of_values, 25)), 2),
            "50_percentile": round(float(np.percentile(list_of_values, 50)), 2),
            "75_percentile": round(float(np.percentile(list_of_values, 75)), 2),
            "max": round(float(np.max(list_of_values)), 2)
        }
    else:
        return "no values"


def save_congestion_info(instance, status_quo_metrics: StatusQuoMetrics, flows: list[list[int]]):
    delay_points = []
    list_vehicles_on_arcs = []
    list_travel_times = []
    list_delays = []
    for vehicle, delays in enumerate(status_quo_metrics.delaysOnArcs):
        for position, delay in enumerate(delays):
            arc = instance.trip_routes[vehicle][position]
            if arc == 0:
                continue
            travel_time = instance.travel_times_arcs[arc]
            vehicles_on_arc = flows[vehicle][position]
            slopes = [round(travel_time * x / (60 * instance.capacities_arcs[arc]), 2) for x in
                      instance.inputData.list_of_slopes]
            threshold_capacities = [instance.capacities_arcs[arc] * x for x in
                                    instance.inputData.list_of_thresholds]
            if round(vehicles_on_arc) > 1:
                list_vehicles_on_arcs.append(round(vehicles_on_arc))
                list_delays.append(round(delay / 60, 2)) if round(delay / 60, 2) > 1e-4 else None
                list_travel_times.append((status_quo_metrics.congestedSchedule[vehicle][-1] -
                                          status_quo_metrics.congestedSchedule[vehicle][0]) / 60)
                delay_points.append(
                    {"arc": arc, "delay": round(delay / 60, 2), "vehicles_on_arc": round(vehicles_on_arc),
                     "travel_time": round(travel_time, 2), "length": instance.osmInfoArcsUtilized[arc]["length"],
                     "threshold_capacities": threshold_capacities, "slopes": slopes})
    distribution_flows = get_distribution_info(list_vehicles_on_arcs)
    flows_great_75_perc = [value for value in list_vehicles_on_arcs if value > np.percentile(list_vehicles_on_arcs, 75)]
    distribution_flows_greater_75 = get_distribution_info(flows_great_75_perc)

    distribution_tt = get_distribution_info(list_travel_times)
    distribution_delays = get_distribution_info(list_delays)
    big_m = estimate_big_m_necessary(instance)
    congestion_info = {"big_m": big_m, "total_delay": round(status_quo_metrics.totalDelay / 60, 2),
                       "distribution_flows": distribution_flows,
                       "distribution_flows_great_75_perc": distribution_flows_greater_75,
                       "distribution_tt": distribution_tt,
                       "distribution_delays": distribution_delays,
                       "delay_points": delay_points}
    file = os.path.join(instance.inputData.path_to_results, fr"congestion_info.json")
    with open(file, "w", encoding='utf-8') as f:
        json.dump(congestion_info, f, ensure_ascii=False, indent=4)


def computeSolutionMetrics(instance, releaseTimes):
    congestedSchedule = getCongestedSchedule(instance, releaseTimes)
    freeFlowSchedule = getFreeFlowSchedule(instance, congestedSchedule)
    delaysOnArcs = getDelaysOnArcs(instance, congestedSchedule)
    totalDelay = getTotalDelay(freeFlowSchedule, congestedSchedule)

    return StatusQuoMetrics(congestedSchedule, freeFlowSchedule, delaysOnArcs, releaseTimes, totalDelay)


def printInfoStatusQuoMetrics(statusQuoMetrics):
    print(f"Number of trips in epoch: {len(statusQuoMetrics.congestedSchedule)}")
    print(f"Initial delay epoch: {round(statusQuoMetrics.totalDelay / 60, 2)} [min] "
          f"({round(statusQuoMetrics.totalDelay / len(statusQuoMetrics.congestedSchedule) / 60, 2)} [min] per trip)"
          )
    numTripsWithDelays = len([sum(delays) for delays in statusQuoMetrics.delaysOnArcs if sum(delays) > 1e-6])
    if numTripsWithDelays > 0:
        print(
            f"{numTripsWithDelays}/ {len(statusQuoMetrics.congestedSchedule)} ({round(numTripsWithDelays / len(statusQuoMetrics.congestedSchedule) * 100, 2)} [%]) trips experience some delay "
            f"({round(statusQuoMetrics.totalDelay / numTripsWithDelays / 60, 2)} [min] per 'congested' trip)")


def printHeaderCurrentEpochStatusQuo(epochInstance):
    print("#" * 20)
    print(f"COMPUTING STATUS QUO FOR EPOCH {epochInstance.epochID} - "
          f"START TIME {epochInstance.epochID * epochInstance.inputData.epochSize * 60}")
    print("#" * 20)


def getCurrentEpochStatusQuo(epochInstance: EpochInstance) -> EpochSolution:
    """ Compute the schedule given the fixed decisions of the previous epochs and
    that all the trips in the current epoch start at the earliest departure time """

    epochInstance.clockStartEpoch = datetime.datetime.now().timestamp()
    printHeaderCurrentEpochStatusQuo(epochInstance)
    statusQuoMetrics = computeSolutionMetrics(epochInstance, epochInstance.releaseTimes)
    addConflictingSetsToInstance(epochInstance, statusQuoMetrics.freeFlowSchedule)
    binaries = getConflictBinaries(epochInstance.conflictingSets,
                                   epochInstance.trip_routes,
                                   statusQuoMetrics.congestedSchedule)
    flows = get_flow_from_binaries(epochInstance, binaries.gamma)
    # save_congestion_info(epochInstance, statusQuoMetrics, flows)
    printInfoStatusQuoMetrics(statusQuoMetrics)
    printInfoArcsUtilized(epochInstance)
    printInfoLengthTrips(epochInstance, statusQuoMetrics.congestedSchedule, statusQuoMetrics.freeFlowSchedule,
                         statusQuoMetrics.delaysOnArcs)
    vehiclesUtilizingArcs = _getVehiclesUtilizingArcs(epochInstance.trip_routes)
    _assertTripsAreNotDuplicated(epochInstance, vehiclesUtilizingArcs)
    printInfoConflictingSetsSizes(epochInstance)
    return EpochSolution(
        delaysOnArcs=statusQuoMetrics.delaysOnArcs,
        freeFlowSchedule=statusQuoMetrics.freeFlowSchedule,
        releaseTimes=statusQuoMetrics.releaseTimes,
        staggeringApplicable=epochInstance.maxStaggeringApplicable[:],
        totalDelay=statusQuoMetrics.totalDelay,
        congestedSchedule=statusQuoMetrics.congestedSchedule,
        staggeringApplied=[0.0] * len(statusQuoMetrics.congestedSchedule),
        totalTravelTime=getTotalTravelTime(statusQuoMetrics.congestedSchedule),
        vehiclesUtilizingArcs=vehiclesUtilizingArcs,
        binaries=binaries
    )
