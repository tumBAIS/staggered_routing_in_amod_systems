from __future__ import annotations
from typing import Callable
import gurobipy as grb
from input_data import SolverParameters, TOLERANCE, ACTIVATE_ASSERTIONS
from utils.aliases import Schedules
from problem.epoch_instance import EpochInstance
from problem.solution import Binaries
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp
from MIP import StaggeredRoutingModel


def get_current_bounds(model: StaggeredRoutingModel, start_solution_time: float) -> None:
    """Update the current bounds (lower and upper) for the optimization problem."""
    new_lower_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
    new_upper_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBST)
    lower_bound_improved = new_lower_bound >= model.get_last_lower_bound()
    upper_bound_improved = new_upper_bound <= model.get_last_upper_bound()

    if lower_bound_improved and upper_bound_improved:
        model.store_lower_bound(new_lower_bound)
        model.store_upper_bound(new_upper_bound)
        model.store_optimization_time(start_solution_time)
        optimality_gap = (
                                 new_upper_bound - new_lower_bound) / new_upper_bound * 100 if new_upper_bound > TOLERANCE else 0
        model.store_optimality_gap(optimality_gap)


def update_remaining_time_for_optimization(model: StaggeredRoutingModel, solver_params: SolverParameters) -> None:
    """Update the remaining time for optimization in the callback."""

    model.set_remaining_time_for_optimization(solver_params)
    if model.get_remaining_time_for_optimization() < 0:
        print("Terminating model from callback - Time limit reached.")
        model.terminate()


def get_callback_solution(model: StaggeredRoutingModel, instance: EpochInstance) -> None:
    """Retrieve the current solution during a callback and update model attributes."""
    model.set_cb_start_times([model.get_continuous_var_cb(vehicle, path[0], "departure")
                              for vehicle, path in enumerate(instance.trip_routes)])
    model.set_cb_total_delay(sum(model.get_continuous_var_cb(vehicle, arc, "delay")
                                 for vehicle, path in enumerate(instance.trip_routes) for arc in path)
                             )

    model.set_flag_update(True)


def assert_schedule(model: StaggeredRoutingModel, congested_schedule: Schedules,
                    delays_on_arcs: Schedules,
                    instance: EpochInstance) -> None:
    """Validate the current schedule and delays."""
    if ACTIVATE_ASSERTIONS:
        for vehicle, (schedule, delays) in enumerate(zip(congested_schedule, delays_on_arcs)):
            first_arc = instance.trip_routes[vehicle][0]
            assert schedule[0] - model.get_continuous_var_bound("lb", first_arc, vehicle, "departure") <= \
                   instance.max_staggering_applicable[
                       vehicle] + TOLERANCE, f"Invalid departure time for the first arc of vehicle {vehicle}."

            for position, arc in enumerate(instance.trip_routes[vehicle]):
                assert model.get_continuous_var_bound("lb", arc, vehicle, "departure") - TOLERANCE <= schedule[
                    position] <= \
                       model.get_continuous_var_bound("ub", arc, vehicle,
                                                      "departure") + TOLERANCE, (f"Invalid departure time "
                                                                                 f"for arc {arc} of vehicle {vehicle}.")
                assert model.get_continuous_var_bound("lb", arc, vehicle, "delay") - TOLERANCE <= delays[position] <= \
                       model.get_continuous_var_bound("ub", arc, vehicle,
                                                      "delay") + TOLERANCE, (f"Invalid delay for arc {arc} "
                                                                             f"of vehicle {vehicle}.")


def set_heuristic_continuous_variables(model: StaggeredRoutingModel, schedule: Schedules, delays_on_arcs: Schedules,
                                       instance: EpochInstance) -> None:
    """Set continuous variables in the model based on the heuristic solution."""
    for vehicle, route in enumerate(instance.trip_routes):
        for position, arc in enumerate(route):
            model.set_continuous_var(vehicle, arc, "departure", schedule[vehicle][position], "cb")
            model.set_continuous_var(vehicle, arc, "delay", delays_on_arcs[vehicle][position], "cb")


def set_heuristic_binary_variables(model: StaggeredRoutingModel, heuristic_binaries: Binaries) -> None:
    """Set binary variables in the model based on the heuristic solution."""
    for arc in model.get_list_conflicting_arcs():
        for first_vehicle, second_vehicle in model.get_arc_conflicting_pairs(arc):
            if heuristic_binaries.gamma[arc][first_vehicle][second_vehicle] != -1:
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "alpha",
                                          heuristic_binaries.alpha[arc][first_vehicle][second_vehicle], "cb")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "beta",
                                          heuristic_binaries.beta[arc][first_vehicle][second_vehicle], "cb")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "gamma",
                                          heuristic_binaries.gamma[arc][first_vehicle][second_vehicle], "cb")


def set_heuristic_solution(model: StaggeredRoutingModel, instance: EpochInstance,
                           heuristic_solution: cpp.cpp_solution,
                           cpp_simplified_epoch_instance: cpp.cpp_instance) -> None:
    """Apply the heuristic solution to the model if it improves the current solution."""
    print("Setting heuristic solution in callback...")
    schedule = heuristic_solution.get_schedule()
    delays_on_arcs = heuristic_solution.get_delays_on_arcs(cpp_simplified_epoch_instance)
    heuristic_binaries = get_conflict_binaries(instance.conflicting_sets, instance.trip_routes, schedule)
    set_heuristic_binary_variables(model, heuristic_binaries)
    set_heuristic_continuous_variables(model, schedule, delays_on_arcs, instance)
    solution_value = model.cbUseSolution()
    print(f"Heuristic solution accepted with value {solution_value:.0f}")
    model.update()
    if solution_value == 1e+100:
        print("Heuristic solution not accepted - terminating model.")
        new_lower_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
        if new_lower_bound > model.get_best_lower_bound():
            model.set_best_lower_bound(new_lower_bound)
        model.terminate()


def callback(instance: EpochInstance, solver_params: SolverParameters,
             cpp_local_search: cpp.cpp_local_search,
             cpp_simplified_epoch_instance: cpp.cpp_instance) -> Callable:
    """Define the callback function for Gurobi.
    """

    def call_local_search(model: StaggeredRoutingModel, where: int) -> None:
        if where == grb.GRB.Callback.MIP:
            get_current_bounds(model, solver_params.start_algorithm_clock)
            update_remaining_time_for_optimization(model, solver_params)

        if where == grb.GRB.Callback.MIPSOL:
            get_callback_solution(model, instance)
            model.set_improvement_clock()
            model.set_best_upper_bound(model.get_cb_total_delay())

        if where == grb.GRB.Callback.MIPNODE and model.get_flag_update():
            model.set_flag_update(False)
            heuristic_solution = cpp_local_search.run(model.get_cb_start_times())
            if is_solution_improving(model, heuristic_solution):
                set_heuristic_solution(model, instance, heuristic_solution, cpp_simplified_epoch_instance)

    return call_local_search


def is_solution_improving(model: StaggeredRoutingModel, heuristic_solution: cpp.cpp_solution) -> bool:
    return model.get_cb_total_delay() - heuristic_solution.get_total_delay() > TOLERANCE
