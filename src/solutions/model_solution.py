from input_data import SolverParameters
from problem.epoch_instance import EpochInstance
from problem.solution import Solution
from MIP import StaggeredRoutingModel
import cpp_module as cpp
import math
from input_data import CONSTR_TOLERANCE, TOLERANCE


def get_model_start_times(model: StaggeredRoutingModel, paths: list[list[int]]) -> list[float]:
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
        cpp_epoch_instance: cpp.cpp_instance
) -> Solution:
    """
    Compute the epoch model solution from the optimized model.
    """
    # If optimization is disabled, return the warm start or status quo
    if not solver_params.optimize or not model.get_optimize_flag() or epoch_instance.instance_params.staggering_cap == 0:
        return epoch_warm_start if solver_params.warm_start else epoch_status_quo

    # Retrieve results from the model
    start_times = get_model_start_times(model, epoch_instance.trip_routes)
    cpp_scheduler = cpp.cpp_scheduler(cpp_epoch_instance)
    solution = cpp_scheduler.construct_solution(start_times)

    # Construct and return the model solution
    return Solution(
        delays_on_arcs=solution.get_delays_on_arcs(cpp_epoch_instance),
        free_flow_schedule=cpp_epoch_instance.get_free_flow_schedule(solution.get_start_times()),
        start_times=solution.get_start_times(),
        total_delay=solution.get_total_delay(),
        congested_schedule=solution.get_schedule(),
        total_travel_time=solution.get_total_travel_time(),
    )
