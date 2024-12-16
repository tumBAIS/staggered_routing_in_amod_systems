import dataclasses
from typing import List
from input_data import SolverParameters, ACTIVATE_ASSERTIONS
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp
from utils.classes import Solution
from instance_module.epoch_instance import EpochInstance
from instance_module.instance import Instance
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from congestion_model.core import (get_congested_schedule,
                                   get_free_flow_schedule,
                                   get_delays_on_arcs,
                                   get_total_delay,
                                   )


def get_vehicles_utilizing_arcs(arc_based_shortest_paths: List[List[int]]) -> List[List[int]]:
    """Identify vehicles utilizing each arc."""
    max_arc = max(max(path) for path in arc_based_shortest_paths)
    vehicles_utilizing_arcs = [[] for _ in range(max_arc + 1)]

    for vehicle, path in enumerate(arc_based_shortest_paths):
        for arc in path[:-1]:
            vehicles_utilizing_arcs[arc].append(vehicle)

    return vehicles_utilizing_arcs


def assert_trips_are_not_duplicated(epoch_instance: EpochInstance, vehicles_utilizing_arcs: List[List[int]]) -> None:
    """Validate that trips and conflicting sets do not have duplicates."""
    if ACTIVATE_ASSERTIONS:
        assert sorted(set(epoch_instance.vehicles_original_ids)) == sorted(epoch_instance.vehicles_original_ids), \
            "Duplicate vehicle IDs found in epoch."

        for arc, conflicting_set in enumerate(epoch_instance.conflicting_sets):
            if conflicting_set:
                assert sorted(set(conflicting_set)) == sorted(conflicting_set), \
                    f"Duplicate values in conflicting set for arc {arc}."
                assert sorted(set(vehicles_utilizing_arcs[arc])) == sorted(vehicles_utilizing_arcs[arc]), \
                    f"Duplicate values in vehicles utilizing arcs for arc {arc}."


@dataclasses.dataclass
class StatusQuoMetrics:
    """Metrics related to the status quo solution."""
    congested_schedule: List[List[float]]
    free_flow_schedule: List[List[float]]
    delays_on_arcs: List[List[float]]
    release_times: List[float]
    total_delay: float


def compute_solution_metrics(instance: Instance, release_times: List[float],
                             solver_params: SolverParameters) -> StatusQuoMetrics:
    """Compute metrics for a solution, including schedules and delays."""
    congested_schedule = get_congested_schedule(instance, release_times, solver_params)
    free_flow_schedule = get_free_flow_schedule(instance, congested_schedule)
    delays_on_arcs = get_delays_on_arcs(instance, congested_schedule)
    total_delay = get_total_delay(free_flow_schedule, congested_schedule)

    return StatusQuoMetrics(
        congested_schedule=congested_schedule,
        free_flow_schedule=free_flow_schedule,
        delays_on_arcs=delays_on_arcs,
        release_times=release_times,
        total_delay=total_delay,
    )


def print_epoch_status_header(epoch_instance: EpochInstance, epoch_size: int) -> None:
    """Print header for the current epoch's status quo computation."""


def get_cpp_epoch_instance(instance: EpochInstance, solver_params: SolverParameters) -> cpp.cpp_instance:
    """Create a CPP instance for the given epoch."""
    return cpp.cpp_instance(
        set_of_vehicle_paths=instance.trip_routes,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        list_of_slopes=instance.instance_params.list_of_slopes,
        list_of_thresholds=instance.instance_params.list_of_thresholds,
        parameters=[solver_params.algorithm_time_limit],
        release_times=instance.release_times,
        deadlines=instance.deadlines,
        lb_travel_time=instance.get_lb_travel_time()
    )


def get_epoch_status_quo(epoch_instance: EpochInstance, solver_params: SolverParameters) -> Solution:
    """Compute the status quo solution for the current epoch."""
    cpp_epoch_instance = get_cpp_epoch_instance(epoch_instance, solver_params)
    cpp_scheduler = cpp.cpp_scheduler(cpp_epoch_instance)
    cpp_status_quo = cpp_scheduler.construct_solution(epoch_instance.release_times)

    delays_on_arcs = cpp_status_quo.get_delays_on_arcs(cpp_epoch_instance)
    free_flow_schedule = cpp_epoch_instance.get_free_flow_schedule(cpp_status_quo.get_start_times())
    add_conflicting_sets_to_instance(epoch_instance, free_flow_schedule)

    binaries = get_conflict_binaries(
        epoch_instance.conflicting_sets,
        epoch_instance.trip_routes,
        cpp_status_quo.get_schedule(),
    )

    vehicles_utilizing_arcs = get_vehicles_utilizing_arcs(epoch_instance.trip_routes)
    assert_trips_are_not_duplicated(epoch_instance, vehicles_utilizing_arcs)

    status_quo = Solution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        release_times=cpp_status_quo.get_start_times(),
        staggering_applicable=epoch_instance.max_staggering_applicable[:],
        total_delay=cpp_status_quo.get_total_delay(),
        congested_schedule=cpp_status_quo.get_schedule(),
        staggering_applied=[0.0] * len(free_flow_schedule),
        total_travel_time=cpp_status_quo.get_total_travel_time(),
        vehicles_utilizing_arcs=vehicles_utilizing_arcs,
        binaries=binaries,
    )

    status_quo.print_congestion_info()
    return status_quo
