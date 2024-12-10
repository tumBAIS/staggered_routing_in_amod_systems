import dataclasses
import datetime
from typing import List

from input_data import SolverParameters
from congestion_model.conflict_binaries import get_conflict_binaries
from utils.prints import (
    print_info_conflicting_sets_sizes,
    print_info_arcs_utilized,
    print_info_length_trips,
)
from utils.classes import EpochSolution
from instance_module.epoch_instance import EpochInstance
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from congestion_model.core import (
    get_total_travel_time,
    get_congested_schedule,
    get_free_flow_schedule,
    get_delays_on_arcs,
    get_total_delay,
)
from input_data import ACTIVATE_ASSERTIONS


def get_vehicles_utilizing_arcs(arc_based_shortest_paths: List[List[int]]) -> List[List[int]]:
    """
    Identify vehicles utilizing each arc.

    Args:
        arc_based_shortest_paths (List[List[int]]): Shortest paths for all vehicles.

    Returns:
        List[List[int]]: Vehicles using each arc.
    """
    max_arc = max(max(path) for path in arc_based_shortest_paths)
    vehicles_utilizing_arcs = [[] for _ in range(max_arc + 1)]

    for vehicle, path in enumerate(arc_based_shortest_paths):
        for arc in path[:-1]:
            vehicles_utilizing_arcs[arc].append(vehicle)

    return vehicles_utilizing_arcs


def assert_trips_are_not_duplicated(epoch_instance: EpochInstance, vehicles_utilizing_arcs: List[List[int]]):
    """
    Validate that trips and conflicting sets do not have duplicates.
    """
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
    congested_schedule: List[List[float]]
    free_flow_schedule: List[List[float]]
    delays_on_arcs: List[List[float]]
    release_times: List[float]
    total_delay: float


def compute_solution_metrics(instance: EpochInstance, release_times: List[float],
                             solver_params: SolverParameters) -> StatusQuoMetrics:
    """
    Compute various metrics for a solution, including schedules and delays.
    """
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


def print_status_quo_metrics(status_quo_metrics: StatusQuoMetrics):
    """
    Print details about the status quo metrics for an epoch.
    """
    print(f"Number of trips in epoch: {len(status_quo_metrics.congested_schedule)}")
    print(f"Initial delay epoch: {round(status_quo_metrics.total_delay / 60, 2)} [min] "
          f"({round(status_quo_metrics.total_delay / len(status_quo_metrics.congested_schedule) / 60, 2)} [min] per trip)")

    trips_with_delays = [
        sum(delays) for delays in status_quo_metrics.delays_on_arcs if sum(delays) > 1e-6
    ]
    if trips_with_delays:
        num_trips_with_delays = len(trips_with_delays)
        print(
            f"{num_trips_with_delays} / {len(status_quo_metrics.congested_schedule)} "
            f"({round(num_trips_with_delays / len(status_quo_metrics.congested_schedule) * 100, 2)} [%]) trips experience delays "
            f"({round(status_quo_metrics.total_delay / num_trips_with_delays / 60, 2)} [min] per delayed trip)"
        )


def print_epoch_status_header(epoch_instance: EpochInstance, epoch_size: int):
    """
    Print a header for the current epoch's status quo computation.
    """
    print("#" * 20)
    print(f"COMPUTING STATUS QUO FOR EPOCH {epoch_instance.epoch_id} - "
          f"START TIME {epoch_instance.epoch_id * epoch_size * 60} seconds")
    print("#" * 20)


def get_current_epoch_status_quo(epoch_instance: EpochInstance, solver_params: SolverParameters) -> EpochSolution:
    """
    Compute the schedule for the current epoch under the status quo scenario.

    Args:
        epoch_instance (EpochInstance): The instance for the current epoch.
        solver_params (SolverParameters): Solver parameters.

    Returns:
        EpochSolution: The computed solution for the current epoch.
    """
    epoch_instance.clock_start_epoch = datetime.datetime.now().timestamp()
    print_epoch_status_header(epoch_instance, epoch_size=solver_params.epoch_size)

    status_quo_metrics = compute_solution_metrics(
        instance=epoch_instance,
        release_times=epoch_instance.release_times,
        solver_params=solver_params,
    )

    add_conflicting_sets_to_instance(epoch_instance, status_quo_metrics.free_flow_schedule)

    binaries = get_conflict_binaries(
        epoch_instance.conflicting_sets,
        epoch_instance.trip_routes,
        status_quo_metrics.congested_schedule,
    )

    print_status_quo_metrics(status_quo_metrics)
    print_info_arcs_utilized(epoch_instance)
    print_info_length_trips(
        epoch_instance,
        status_quo_metrics.congested_schedule,
        status_quo_metrics.free_flow_schedule,
        status_quo_metrics.delays_on_arcs,
    )

    vehicles_utilizing_arcs = get_vehicles_utilizing_arcs(epoch_instance.trip_routes)
    assert_trips_are_not_duplicated(epoch_instance, vehicles_utilizing_arcs)
    print_info_conflicting_sets_sizes(epoch_instance)

    return EpochSolution(
        delays_on_arcs=status_quo_metrics.delays_on_arcs,
        free_flow_schedule=status_quo_metrics.free_flow_schedule,
        release_times=status_quo_metrics.release_times,
        staggering_applicable=epoch_instance.max_staggering_applicable[:],
        total_delay=status_quo_metrics.total_delay,
        congested_schedule=status_quo_metrics.congested_schedule,
        staggering_applied=[0.0] * len(status_quo_metrics.congested_schedule),
        total_travel_time=get_total_travel_time(status_quo_metrics.congested_schedule),
        vehicles_utilizing_arcs=vehicles_utilizing_arcs,
        binaries=binaries,
    )
