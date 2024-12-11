import datetime
from input_data import SolverParameters
from utils.aliases import VehicleSchedules
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution
from congestion_model.core import (
    get_free_flow_schedule,
    get_total_travel_time,
    get_delays_on_arcs,
    get_staggering_applicable,
)
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp


def _run_local_search(
        solution: EpochSolution, instance: EpochInstance, solver_params: SolverParameters
) -> VehicleSchedules:
    """
    Performs local search optimization to compute a warm start solution.
    """
    print("Computing warm start solution")
    instance.due_dates = instance.deadlines[:]
    time_remaining = _compute_remaining_time(instance, solver_params)

    start_time = datetime.datetime.now().timestamp()
    cpp_parameters = [time_remaining]

    congested_schedule = cpp.cpp_local_search(
        release_times=solution.release_times,
        remaining_time_slack=solution.staggering_applicable,
        staggering_applied=solution.staggering_applied,
        conflicting_sets=instance.conflicting_sets,
        earliest_departure_times=instance.earliest_departure_times,
        latest_departure_times=instance.latest_departure_times,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        trip_routes=instance.trip_routes,
        deadlines=instance.deadlines,
        list_of_slopes=instance.input_data.list_of_slopes,
        list_of_thresholds=instance.input_data.list_of_thresholds,
        parameters=cpp_parameters,
        lb_travel_time=instance.get_lb_travel_time(),
    )

    elapsed_time = datetime.datetime.now().timestamp() - start_time
    print("Time required to compute warm start solution: ", elapsed_time)
    return congested_schedule


def _compute_remaining_time(instance: EpochInstance, solver_params: SolverParameters) -> float:
    """
    Calculates the remaining time for optimization based on algorithm and epoch limits.
    """
    algorithm_time_remaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_time_remaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    return max(0.0, min(algorithm_time_remaining, epoch_time_remaining))


def _is_time_left_for_optimization(instance: EpochInstance, solver_params: SolverParameters) -> bool:
    """
    Checks whether there is sufficient time left for optimization.
    """
    return _compute_remaining_time(instance, solver_params) > 1e-6


def get_epoch_warm_start(
        epoch_instance: EpochInstance, epoch_status_quo: EpochSolution, solver_params: SolverParameters
) -> EpochSolution:
    """
    Computes the warm start solution for the given epoch.

    If the solver parameters allow improving the warm start and there is time left for optimization,
    performs a local search. Otherwise, returns the status quo.
    """
    if solver_params.improve_warm_start and _is_time_left_for_optimization(epoch_instance, solver_params):
        congested_schedule = _run_local_search(epoch_status_quo, epoch_instance, solver_params)
    else:
        if not _is_time_left_for_optimization(epoch_instance, solver_params):
            print("No remaining time for optimization - ", end="")
        print("Using status quo as warm start")
        return epoch_status_quo

    # Compute necessary metrics for the warm start solution
    release_times = [schedule[0] for schedule in congested_schedule]
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    staggering_applied = [
        congested_schedule[vehicle][0] - release_time
        for vehicle, release_time in enumerate(epoch_status_quo.release_times)
    ]
    staggering_applicable = get_staggering_applicable(epoch_instance, staggering_applied)
    delays_on_arcs = get_delays_on_arcs(epoch_instance, congested_schedule)
    total_delay = sum(sum(delays) for delays in delays_on_arcs)
    binaries = get_conflict_binaries(epoch_instance.conflicting_sets, epoch_instance.trip_routes, congested_schedule)
    total_travel_time = get_total_travel_time(congested_schedule)

    warm_start = EpochSolution(
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        release_times=release_times,
        staggering_applicable=staggering_applicable,
        binaries=binaries,
        free_flow_schedule=free_flow_schedule,
        staggering_applied=staggering_applied,
        total_travel_time=total_travel_time,
        vehicles_utilizing_arcs=epoch_status_quo.vehicles_utilizing_arcs,
    )

    print(f"The delay of the warm start is {total_delay / total_travel_time:.2%} of the travel time")
    return warm_start
