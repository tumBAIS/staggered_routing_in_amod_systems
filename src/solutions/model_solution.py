from input_data import SolverParameters
from congestion_model.core import (
    get_free_flow_schedule,
    get_total_travel_time,
)
from instance_module.epoch_instance import EpochInstance
from utils.classes import Solution
from MIP import StaggeredRoutingModel


def get_model_release_times(model: StaggeredRoutingModel, paths: list[list[int]]) -> list[float]:
    """Retrieve the release times from the model for each vehicle."""
    return [model.get_continuous_var_value(vehicle, path[0], "departure") for vehicle, path in enumerate(paths)]


def get_model_schedule(model: StaggeredRoutingModel, paths: list[list[int]]) -> list[list[float]]:
    """Retrieve the complete schedule from the model for each vehicle."""
    return [[model.get_continuous_var_value(vehicle, arc, "departure") for arc in path] for vehicle, path in
            enumerate(paths)]


def get_model_delay_on_arcs(model: StaggeredRoutingModel, paths: list[list[int]]) -> list[list[float]]:
    """Retrieve the delay on arcs from the model for each vehicle."""
    return [[model.get_continuous_var_value(vehicle, arc, "delay")
             for arc in path] for vehicle, path in enumerate(paths)]


def get_staggering_applied(release_times_solution: list[float], release_times_status_quo: list[float]) -> list[float]:
    """Compute the staggering applied by comparing solution release times with the status quo."""
    return [
        release_times_solution[i] - release_times_status_quo[i]
        for i in range(len(release_times_status_quo))
    ]


def get_epoch_model_solution(
        model: StaggeredRoutingModel,
        epoch_instance: EpochInstance,
        epoch_status_quo: Solution,
        epoch_warm_start: Solution,
        solver_params: SolverParameters,
) -> Solution:
    """
    Compute the epoch model solution from the optimized model.
    """
    # If optimization is disabled, return the warm start or status quo
    if not solver_params.optimize or not model.get_optimize_flag() or epoch_instance.instance_params.staggering_cap == 0:
        return epoch_warm_start if solver_params.warm_start else epoch_status_quo

    # Retrieve results from the model
    total_delay = model.get_objective_value()
    release_times = get_model_release_times(model, epoch_instance.trip_routes)
    congested_schedule = get_model_schedule(model, epoch_instance.trip_routes)
    delays_on_arcs = get_model_delay_on_arcs(model, epoch_instance.trip_routes)
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    staggering_applied = get_staggering_applied(release_times, epoch_status_quo.release_times)
    total_travel_time = get_total_travel_time(congested_schedule)

    # Construct and return the model solution
    return Solution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        release_times=release_times,
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        vehicles_utilizing_arcs=epoch_status_quo.vehicles_utilizing_arcs,
        total_travel_time=total_travel_time,
    )
