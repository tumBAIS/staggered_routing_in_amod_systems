import dataclasses
import datetime
import json
import os.path

import numpy as np

from congestion_model.conflict_binaries import get_conflict_binaries, get_flow_from_binaries
from utils.prints import print_info_conflicting_sets_sizes, \
    print_info_arcs_utilized, print_info_length_trips
from utils.classes import EpochSolution
from instanceModule.epoch_instance import EpochInstance
from conflicting_sets.get import add_conflicting_sets_to_instance, estimate_big_m_necessary
from congestion_model.core import get_total_travel_time, get_congested_schedule, get_free_flow_schedule, \
    get_delays_on_arcs, get_total_delay
from input_data import ACTIVATE_ASSERTIONS, MIN_SET_CAPACITY


def _get_vehicles_utilizing_arcs(arcBasedShortestPaths: list[list[int]]) -> list[list[int]]:
    vehiclesUtilizingArcs = [[] for _ in range(max([max(path) for path in arcBasedShortestPaths]) + 1)]  # type: ignore
    for vehicle, path in enumerate(arcBasedShortestPaths):
        for arc in path[:-1]:
            vehiclesUtilizingArcs[arc].append(vehicle)

    return vehiclesUtilizingArcs


def _assert_trips_are_not_duplicated(epochInstance, vehiclesUtilizingArcs):
    if ACTIVATE_ASSERTIONS:
        assert sorted(list(set(epochInstance.vehicles_original_ids))) == sorted(epochInstance.vehicles_original_ids), \
            f"vehicles IDs repeat themselves"
    for arc, conflictingSet in enumerate(epochInstance.conflicting_sets):
        if conflictingSet:
            assert sorted(list(set(conflictingSet))) == sorted(conflictingSet), \
                f"repetitions in conflicting set"
            assert sorted(list(set(vehiclesUtilizingArcs[arc]))) == sorted(vehiclesUtilizingArcs[arc]), \
                f"repetitions in conflicting set"


@dataclasses.dataclass
class StatusQuoMetrics:
    congested_schedule: list[list[float]]
    free_flow_schedule: list[list[float]]
    delays_on_arcs: list[list[float]]
    release_times: list[float]
    total_delay: float


def compute_vehicles_on_arc_from_delay(delay, instance, arc, first_capacity, second_capacity):
    second_slope = instance.travel_times_arcs[arc] * instance.input_data.slopeSecondLine / \
                   max(instance.capacities_arcs[arc], MIN_SET_CAPACITY)
    third_slope = instance.travel_times_arcs[arc] * instance.input_data.slopeThirdLine / \
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
    for vehicle, delays in enumerate(status_quo_metrics.delays_on_arcs):
        for position, delay in enumerate(delays):
            arc = instance.trip_routes[vehicle][position]
            if arc == 0:
                continue
            travel_time = instance.travel_times_arcs[arc]
            vehicles_on_arc = flows[vehicle][position]
            slopes = [round(travel_time * x / (60 * instance.capacities_arcs[arc]), 2) for x in
                      instance.input_data.list_of_slopes]
            threshold_capacities = [instance.capacities_arcs[arc] * x for x in
                                    instance.input_data.list_of_thresholds]
            if round(vehicles_on_arc) > 1:
                list_vehicles_on_arcs.append(round(vehicles_on_arc))
                list_delays.append(round(delay / 60, 2)) if round(delay / 60, 2) > 1e-4 else None
                list_travel_times.append((status_quo_metrics.congested_schedule[vehicle][-1] -
                                          status_quo_metrics.congested_schedule[vehicle][0]) / 60)
                delay_points.append(
                    {"arc": arc, "delay": round(delay / 60, 2), "vehicles_on_arc": round(vehicles_on_arc),
                     "travel_time": round(travel_time, 2), "length": instance.osm_info_arcs_utilized[arc]["length"],
                     "threshold_capacities": threshold_capacities, "slopes": slopes})
    distribution_flows = get_distribution_info(list_vehicles_on_arcs)
    flows_great_75_perc = [value for value in list_vehicles_on_arcs if value > np.percentile(list_vehicles_on_arcs, 75)]
    distribution_flows_greater_75 = get_distribution_info(flows_great_75_perc)

    distribution_tt = get_distribution_info(list_travel_times)
    distribution_delays = get_distribution_info(list_delays)
    big_m = estimate_big_m_necessary(instance)
    congestion_info = {"big_m": big_m, "total_delay": round(status_quo_metrics.total_delay / 60, 2),
                       "distribution_flows": distribution_flows,
                       "distribution_flows_great_75_perc": distribution_flows_greater_75,
                       "distribution_tt": distribution_tt,
                       "distribution_delays": distribution_delays,
                       "delay_points": delay_points}
    file = os.path.join(instance.input_data.path_to_results, fr"congestion_info.json")
    with open(file, "w", encoding='utf-8') as f:
        json.dump(congestion_info, f, ensure_ascii=False, indent=4)


def compute_solution_metrics(instance, releaseTimes):
    congestedSchedule = get_congested_schedule(instance, releaseTimes)
    freeFlowSchedule = get_free_flow_schedule(instance, congestedSchedule)
    delaysOnArcs = get_delays_on_arcs(instance, congestedSchedule)
    totalDelay = get_total_delay(freeFlowSchedule, congestedSchedule)

    return StatusQuoMetrics(congestedSchedule, freeFlowSchedule, delaysOnArcs, releaseTimes, totalDelay)


def print_info_status_quo_metrics(statusQuoMetrics):
    print(f"Number of trips in epoch: {len(statusQuoMetrics.congested_schedule)}")
    print(f"Initial delay epoch: {round(statusQuoMetrics.total_delay / 60, 2)} [min] "
          f"({round(statusQuoMetrics.total_delay / len(statusQuoMetrics.congested_schedule) / 60, 2)} [min] per trip)"
          )
    numTripsWithDelays = len([sum(delays) for delays in statusQuoMetrics.delays_on_arcs if sum(delays) > 1e-6])
    if numTripsWithDelays > 0:
        print(
            f"{numTripsWithDelays}/ {len(statusQuoMetrics.congested_schedule)} ({round(numTripsWithDelays / len(statusQuoMetrics.congested_schedule) * 100, 2)} [%]) trips experience some delay "
            f"({round(statusQuoMetrics.total_delay / numTripsWithDelays / 60, 2)} [min] per 'congested' trip)")


def print_header_current_epoch_status_quo(epochInstance):
    print("#" * 20)
    print(f"COMPUTING STATUS QUO FOR EPOCH {epochInstance.epoch_id} - "
          f"START TIME {epochInstance.epoch_id * epochInstance.input_data.epoch_size * 60}")
    print("#" * 20)


def get_current_epoch_status_quo(epochInstance: EpochInstance) -> EpochSolution:
    """ Compute the schedule given the fixed decisions of the previous epochs and
    that all the trips in the current epoch start at the earliest departure time """

    epochInstance.clock_start_epoch = datetime.datetime.now().timestamp()
    print_header_current_epoch_status_quo(epochInstance)
    statusQuoMetrics = compute_solution_metrics(epochInstance, epochInstance.release_times)
    add_conflicting_sets_to_instance(epochInstance, statusQuoMetrics.free_flow_schedule)
    binaries = get_conflict_binaries(epochInstance.conflicting_sets,
                                     epochInstance.trip_routes,
                                     statusQuoMetrics.congested_schedule)
    flows = get_flow_from_binaries(epochInstance, binaries.gamma)
    # save_congestion_info(epochInstance, statusQuoMetrics, flows)
    print_info_status_quo_metrics(statusQuoMetrics)
    print_info_arcs_utilized(epochInstance)
    print_info_length_trips(epochInstance, statusQuoMetrics.congested_schedule, statusQuoMetrics.free_flow_schedule,
                            statusQuoMetrics.delays_on_arcs)
    vehiclesUtilizingArcs = _get_vehicles_utilizing_arcs(epochInstance.trip_routes)
    _assert_trips_are_not_duplicated(epochInstance, vehiclesUtilizingArcs)
    print_info_conflicting_sets_sizes(epochInstance)
    return EpochSolution(
        delays_on_arcs=statusQuoMetrics.delays_on_arcs,
        free_flow_schedule=statusQuoMetrics.free_flow_schedule,
        release_times=statusQuoMetrics.release_times,
        staggering_applicable=epochInstance.max_staggering_applicable[:],
        total_delay=statusQuoMetrics.total_delay,
        congested_schedule=statusQuoMetrics.congested_schedule,
        staggering_applied=[0.0] * len(statusQuoMetrics.congested_schedule),
        total_travel_time=get_total_travel_time(statusQuoMetrics.congested_schedule),
        vehicles_utilizing_arcs=vehiclesUtilizingArcs,
        binaries=binaries
    )
