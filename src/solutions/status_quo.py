import dataclasses
import datetime
from congestion_model.conflict_binaries import get_conflict_binaries
from utils.prints import print_info_conflicting_sets_sizes, \
    print_info_arcs_utilized, print_info_length_trips
from utils.classes import EpochSolution
from instance_module.epoch_instance import EpochInstance
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from congestion_model.core import get_total_travel_time, get_congested_schedule, get_free_flow_schedule, \
    get_delays_on_arcs, get_total_delay
from input_data import ACTIVATE_ASSERTIONS


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
