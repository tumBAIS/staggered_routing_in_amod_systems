from __future__ import annotations

import datetime
import itertools
from typing import Callable

import gurobipy as grb
from gurobipy import Model

from input_data import SolverParameters, TOLERANCE, ACTIVATE_ASSERTIONS
from utils.classes import CompleteSolution, HeuristicSolution
from utils.aliases import VehicleSchedules
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


def get_callback_solution(model: StaggeredRoutingModel, instance: EpochInstance, status_quo: CompleteSolution) -> None:
    """Retrieve the current solution during a callback and update model attributes."""
    model._cbReleaseTimes = [model.get_continuous_var_cb(vehicle, path[0], "departure")
                             for vehicle, path in enumerate(instance.trip_routes)]
    model.set_cb_total_delay(sum(model.get_continuous_var_cb(vehicle, arc, "delay")
                                 for vehicle, path in enumerate(instance.trip_routes) for arc in path)
                             )
    model._cbStaggeringApplied = [
        release_time - status_quo.congested_schedule[vehicle][0]
        for vehicle, release_time in enumerate(model.get_cb_release_times())
    ]
    model._cbRemainingTimeSlack = get_staggering_applicable(instance, model._cbStaggeringApplied)
    model.set_flag_update(True)


def assert_schedule(model: Model, congested_schedule: VehicleSchedules, delays_on_arcs: VehicleSchedules,
                    instance: EpochInstance) -> None:
    """Validate the current schedule and delays."""
    if ACTIVATE_ASSERTIONS:
        for vehicle, (schedule, delays) in enumerate(zip(congested_schedule, delays_on_arcs)):
            first_arc = instance.trip_routes[vehicle][0]
            assert schedule[0] - model._departure[vehicle][first_arc]._lb <= \
                   instance.max_staggering_applicable[vehicle] + 1e-6, \
                f"Invalid departure time for the first arc of vehicle {vehicle}."

            for position, arc in enumerate(instance.trip_routes[vehicle]):
                assert model._departure[vehicle][arc]._lb - 1e-6 <= schedule[position] <= model._departure[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid departure time for arc {arc} of vehicle {vehicle}."
                assert model._delay[vehicle][arc]._lb - 1e-6 <= delays[position] <= model._delay[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid delay for arc {arc} of vehicle {vehicle}."


def get_heuristic_solution(model: Model, instance: EpochInstance, solver_params: SolverParameters) -> HeuristicSolution:
    """Generate a heuristic solution using the local search module."""
    model._flagUpdate = False
    cpp_parameters = [solver_params.algorithm_time_limit]
    congested_schedule = cpp.cpp_local_search(
        release_times=model._cbReleaseTimes,
        remaining_time_slack=model._cbRemainingTimeSlack,
        staggering_applied=model._cbStaggeringApplied,
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


def set_heuristic_continuous_variables(model: Model, heuristic_solution: HeuristicSolution) -> None:
    """Set continuous variables in the model based on the heuristic solution."""
    for vehicle in model._departure:
        for position, arc in enumerate(model._departure[vehicle]):
            model.cbSetSolution(model._departure[vehicle][arc],
                                heuristic_solution.congested_schedule[vehicle][position])
            if isinstance(model._delay[vehicle][arc], grb.Var):
                model.cbSetSolution(model._delay[vehicle][arc], heuristic_solution.delays_on_arcs[vehicle][position])


def set_heuristic_binary_variables(model: Model, heuristic_solution: HeuristicSolution) -> None:
    """Set binary variables in the model based on the heuristic solution."""
    for arc in model._gamma:
        for first_vehicle, second_vehicle in itertools.combinations(model._gamma[arc], 2):
            if heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle] != -1:
                if isinstance(model._alpha[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(
                        model._alpha[arc][first_vehicle][second_vehicle],
                        heuristic_solution.binaries.alpha[arc][first_vehicle][second_vehicle]
                    )
                if isinstance(model._beta[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(
                        model._beta[arc][first_vehicle][second_vehicle],
                        heuristic_solution.binaries.beta[arc][first_vehicle][second_vehicle]
                    )
                if isinstance(model._gamma[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(
                        model._gamma[arc][first_vehicle][second_vehicle],
                        heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle]
                    )


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
        set_heuristic_continuous_variables(model, heuristic_solution)
        solution_status = model.cbUseSolution()
        print(f"Model.cbUseSolution() returned {solution_status}")
        model.update()
        if solution_status == 1e+100:
            print("Heuristic solution not accepted - terminating model.")
            suspend_procedure(heuristic_solution, model, instance)


def callback(instance: EpochInstance, status_quo: CompleteSolution, solver_params: SolverParameters) -> Callable:
    """Define the callback function for Gurobi."""

    def call_local_search(model: StaggeredRoutingModel, where: int) -> None:
        if where == grb.GRB.Callback.MIP:
            get_current_bounds(model, instance.start_solution_time)
            update_remaining_time_for_optimization(model, instance, solver_params)

        if where == grb.GRB.Callback.MIPSOL:
            get_callback_solution(model, instance, status_quo)
            model._improvementClock = datetime.datetime.now().timestamp()
            model._bestUpperBound = model.get_cb_total_delay()

        if where == grb.GRB.Callback.MIPNODE and model.get_flag_update():
            heuristic_solution = get_heuristic_solution(model, instance, solver_params)
            set_heuristic_solution(model, heuristic_solution, instance)

    return call_local_search
