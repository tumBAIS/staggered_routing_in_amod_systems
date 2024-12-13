from __future__ import annotations
from typing import Callable

import gurobipy as grb

from input_data import SolverParameters, TOLERANCE, ACTIVATE_ASSERTIONS
from utils.classes import Solution, HeuristicSolution
from utils.aliases import TripSchedules
from instance_module.epoch_instance import EpochInstance
from MIP.support import save_solution_in_external_file
from congestion_model.core import get_delays_on_arcs, get_staggering_applicable
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


def update_remaining_time_for_optimization(model: StaggeredRoutingModel, instance: EpochInstance,
                                           solver_params: SolverParameters) -> None:
    """Update the remaining time for optimization in the callback."""

    model.set_remaining_time_for_optimization(solver_params, instance.start_solution_time)
    if model.get_remaining_time_for_optimization() < 0:
        print("Terminating model from callback - Time limit reached.")
        model.terminate()


def get_callback_solution(model: StaggeredRoutingModel, instance: EpochInstance, status_quo: Solution) -> None:
    """Retrieve the current solution during a callback and update model attributes."""
    model.set_cb_release_times([model.get_continuous_var_cb(vehicle, path[0], "departure")
                                for vehicle, path in enumerate(instance.trip_routes)])
    model.set_cb_total_delay(sum(model.get_continuous_var_cb(vehicle, arc, "delay")
                                 for vehicle, path in enumerate(instance.trip_routes) for arc in path)
                             )
    model.set_cb_staggering_applied([
        release_time - status_quo.congested_schedule[vehicle][0]
        for vehicle, release_time in enumerate(model.get_cb_release_times())
    ])
    model.set_cb_remaining_time_slack(get_staggering_applicable(instance, model.get_cb_staggering_applied()))
    model.set_flag_update(True)


def assert_schedule(model: StaggeredRoutingModel, congested_schedule: TripSchedules,
                    delays_on_arcs: TripSchedules,
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


def get_heuristic_solution(model: StaggeredRoutingModel, instance: EpochInstance,
                           solver_params: SolverParameters) -> HeuristicSolution:
    """Generate a heuristic solution using the local search module."""
    model.set_flag_update(False)
    cpp_parameters = [solver_params.algorithm_time_limit]
    congested_schedule = cpp.cpp_local_search(
        release_times=model.get_cb_release_times(),
        remaining_time_slack=model.get_cb_remaining_time_slack(),
        staggering_applied=model.get_cb_staggering_applied(),
        conflicting_sets=instance.conflicting_sets,
        earliest_departure_times=instance.earliest_departure_times,
        latest_departure_times=instance.latest_departure_times,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        trip_routes=instance.trip_routes,
        deadlines=instance.deadlines,
        list_of_slopes=instance.instance_params.list_of_slopes,
        list_of_thresholds=instance.instance_params.list_of_thresholds,
        parameters=cpp_parameters,
        lb_travel_time=instance.get_lb_travel_time()
    )

    delays_on_arcs = get_delays_on_arcs(instance, congested_schedule)
    assert_schedule(model, congested_schedule, delays_on_arcs, instance)
    binaries = get_conflict_binaries(instance.conflicting_sets, instance.trip_routes, congested_schedule)
    total_delay = sum(sum(delays_on_arc_vehicle) for delays_on_arc_vehicle in delays_on_arcs)

    return HeuristicSolution(
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        binaries=binaries,
        total_delay=total_delay
    )


def set_heuristic_continuous_variables(model: StaggeredRoutingModel, heuristic_solution: HeuristicSolution,
                                       instance: EpochInstance) -> None:
    """Set continuous variables in the model based on the heuristic solution."""
    for vehicle, route in enumerate(instance.trip_routes):
        for position, arc in enumerate(route):
            model.set_continuous_var(vehicle, arc, "departure",
                                     heuristic_solution.congested_schedule[vehicle][position], "cb")
            model.set_continuous_var(vehicle, arc, "delay", heuristic_solution.delays_on_arcs[vehicle][position],
                                     "cb")


def set_heuristic_binary_variables(model: StaggeredRoutingModel, heuristic_solution: HeuristicSolution) -> None:
    """Set binary variables in the model based on the heuristic solution."""
    for arc in model.get_list_conflicting_arcs():
        for first_vehicle, second_vehicle in model.get_arc_conflicting_pairs(arc):
            if heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle] != -1:
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "alpha",
                                          heuristic_solution.binaries.alpha[arc][first_vehicle][second_vehicle], "cb")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "beta",
                                          heuristic_solution.binaries.beta[arc][first_vehicle][second_vehicle], "cb")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "gamma",
                                          heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle], "cb")


def suspend_procedure(heuristic_solution: HeuristicSolution, model: StaggeredRoutingModel,
                      instance: EpochInstance) -> None:
    """Save the heuristic solution and terminate the model if needed."""
    save_solution_in_external_file(heuristic_solution, instance)
    new_lower_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
    if new_lower_bound > model.get_best_lower_bound():
        model.set_best_lower_bound(new_lower_bound)
    model.terminate()


def set_heuristic_solution(model: StaggeredRoutingModel, heuristic_solution: HeuristicSolution,
                           instance: EpochInstance) -> None:
    """Apply the heuristic solution to the model if it improves the current solution."""
    solution_is_improving = model.get_cb_total_delay() - heuristic_solution.total_delay > TOLERANCE
    if solution_is_improving:
        print("Setting heuristic solution in callback...", end=" ")
        set_heuristic_binary_variables(model, heuristic_solution)
        set_heuristic_continuous_variables(model, heuristic_solution, instance)
        solution_status = model.cbUseSolution()
        print(f"Model.cbUseSolution() returned {solution_status}")
        model.update()
        if solution_status == 1e+100:
            print("Heuristic solution not accepted - terminating model.")
            suspend_procedure(heuristic_solution, model, instance)


def callback(instance: EpochInstance, status_quo: Solution, solver_params: SolverParameters) -> Callable:
    """Define the callback function for Gurobi.
    @rtype: object
    """

    def call_local_search(model: StaggeredRoutingModel, where: int) -> None:
        if where == grb.GRB.Callback.MIP:
            get_current_bounds(model, instance.start_solution_time)
            update_remaining_time_for_optimization(model, instance, solver_params)

        if where == grb.GRB.Callback.MIPSOL:
            get_callback_solution(model, instance, status_quo)
            model.set_improvement_clock()
            model.set_best_upper_bound(model.get_cb_total_delay())

        if where == grb.GRB.Callback.MIPNODE and model.get_flag_update():
            heuristic_solution = get_heuristic_solution(model, instance, solver_params)
            set_heuristic_solution(model, heuristic_solution, instance)

    return call_local_search
