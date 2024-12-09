from input_data import SolverParameters
from congestion_model.core import (
    get_free_flow_schedule,
    get_total_travel_time,
    get_staggering_applicable,
)
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution
from gurobipy import Model
import gurobipy as grb


def get_model_release_times(model: Model, paths: list[list[int]]) -> list[float]:
    """Retrieve the release times from the model."""
    return [model._departure[vehicle][path[0]].X for vehicle, path in enumerate(paths)]


def get_model_schedule(model: Model, paths: list[list[int]]) -> list[list[float]]:
    """Retrieve the schedule from the model."""
    return [[model._departure[vehicle][arc].X for arc in path] for vehicle, path in enumerate(paths)]


def get_model_delay_on_arcs(model: Model, paths: list[list[int]]) -> list[list[float]]:
    """Retrieve the delay on arcs from the model."""
    return [
        [
            model._delay[vehicle][arc].X if isinstance(model._delay[vehicle][arc], grb.Var) else 0
            for arc in path
        ]
        for vehicle, path in enumerate(paths)
    ]


def get_staggering_applied(release_times_solution, release_times_status_quo):
    """Compute the staggering applied."""
    return [
        release_times_solution[i] - release_times_status_quo[i]
        for i in range(len(release_times_status_quo))
    ]


def get_epoch_model_solution(
        model: Model,
        epoch_instance: EpochInstance,
        epoch_status_quo: EpochSolution,
        epoch_warm_start: EpochSolution,
        solver_params: SolverParameters,
) -> EpochSolution:
    """
    Compute the epoch model solution.
    """
    # If optimization is disabled, return warm start or status quo
    if not solver_params.optimize or not model._optimize or epoch_instance.input_data.staggering_cap == 0:
        if not solver_params.warm_start:
            return epoch_status_quo
        return epoch_warm_start

    # Retrieve results from the optimized model
    total_delay = model._totalDelay.X
    release_times = get_model_release_times(model, epoch_instance.trip_routes)
    congested_schedule = get_model_schedule(model, epoch_instance.trip_routes)
    delays_on_arcs = get_model_delay_on_arcs(model, epoch_instance.trip_routes)
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    staggering_applied = get_staggering_applied(release_times, epoch_status_quo.release_times)
    slack = get_staggering_applicable(epoch_instance, staggering_applied)
    total_travel_time = get_total_travel_time(congested_schedule)

    # Construct the solution
    model_solution = EpochSolution(
        delays_on_arcs=delays_on_arcs,
        free_flow_schedule=free_flow_schedule,
        release_times=release_times,
        staggering_applicable=slack,
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        staggering_applied=staggering_applied,
        vehicles_utilizing_arcs=epoch_status_quo.vehicles_utilizing_arcs,
        total_travel_time=total_travel_time,
    )

    return model_solution
