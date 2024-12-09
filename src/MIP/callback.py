from __future__ import annotations

import datetime
import itertools

from input_data import SolverParameters
from MIP.support import save_solution_in_external_file
from congestion_model.core import get_delays_on_arcs, get_staggering_applicable
from gurobipy import Model
from input_data import TOLERANCE, ACTIVATE_ASSERTIONS
from utils.classes import CompleteSolution, HeuristicSolution
from utils.aliases import VehicleSchedules
from instance_module.instance import Instance
import gurobipy as grb
import cpp_module as cpp
from typing import Callable
from congestion_model.conflict_binaries import get_conflict_binaries


def get_current_bounds(model: Model, start_solution_time) -> None:
    lower_bound_improved = model.cbGet(grb.GRB.Callback.MIP_OBJBND) >= model._lowerBound[-1]
    upper_bound_improved = model.cbGet(grb.GRB.Callback.MIP_OBJBST) <= model._upperBound[-1]

    if lower_bound_improved and upper_bound_improved:
        lower_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
        upper_bound = model.cbGet(grb.GRB.Callback.MIP_OBJBST)
        model._lowerBound.append(round(lower_bound, 2))
        model._upperBound.append(round(upper_bound, 2))

        time_spent_in_optimization = datetime.datetime.now().timestamp() - start_solution_time
        model._optimizationTime.append(time_spent_in_optimization)

        optimality_gap = (upper_bound - lower_bound) / upper_bound * 100 if upper_bound > TOLERANCE else 0
        model._optimalityGap.append(round(optimality_gap, 2))


def update_remaining_time_for_optimization(model: Model, instance: Instance, solver_params: SolverParameters) -> None:
    total_optimization_time = solver_params.algorithm_time_limit
    elapsed_time = datetime.datetime.now().timestamp() - instance.start_solution_time

    model._remainingTimeForOptimization = total_optimization_time - elapsed_time

    if model._remainingTimeForOptimization < 0:
        print("Terminating model from callback - Time limit reached")
        model.terminate()


def get_callback_solution(model: Model, instance: Instance, status_quo: CompleteSolution) -> None:
    model._cbReleaseTimes = [model.cbGetSolution(model._departure[vehicle][path[0]])
                             for vehicle, path in enumerate(instance.trip_routes)]
    model._cbTotalDelay = sum(sum(model.cbGetSolution(model._delay[vehicle][arc])
                                  if isinstance(model._delay[vehicle][arc], grb.Var) else 0
                                  for arc in model._delay[vehicle])
                              for vehicle in range(len(model._cbReleaseTimes)))
    model._cbStaggeringApplied = [model._cbReleaseTimes[vehicle] - status_quo.congested_schedule[vehicle][0]
                                  for vehicle in range(len(model._cbReleaseTimes))]
    model._cbRemainingTimeSlack = get_staggering_applicable(instance, model._cbStaggeringApplied)
    model._flagUpdate = True


def assert_schedule(model: Model, congested_schedule: VehicleSchedules, delays_on_arcs: VehicleSchedules,
                    instance: Instance) -> None:
    if ACTIVATE_ASSERTIONS:
        for vehicle, (schedule, delays) in enumerate(zip(congested_schedule, delays_on_arcs)):
            first_arc = instance.trip_routes[vehicle][0]
            assert schedule[0] - model._departure[vehicle][first_arc]._lb <= instance.max_staggering_applicable[
                vehicle] + 1e-6, \
                f"Invalid departure time for the first arc of vehicle {vehicle}"

            for position, arc in enumerate(instance.trip_routes[vehicle]):
                assert model._departure[vehicle][arc]._lb - 1e-6 <= schedule[position] <= model._departure[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid departure time for arc {arc} of vehicle {vehicle} " \
                    f"({model._departure[vehicle][arc]._lb} <= {schedule[position]} <= {model._departure[vehicle][arc]._ub})"
                assert model._delay[vehicle][arc]._lb - 1e-6 <= delays[position] <= model._delay[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid delay for arc {arc} of vehicle {vehicle}"


def get_heuristic_solution(model: Model, instance: Instance, solver_params: SolverParameters) -> HeuristicSolution:
    model._flagUpdate = False
    cpp_parameters = [solver_params.algorithm_time_limit]
    instance.due_dates = instance.deadlines
    congested_schedule = cpp.cppSchedulingLocalSearch(
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
        due_dates=instance.due_dates,
        list_of_slopes=instance.input_data.list_of_slopes,
        list_of_thresholds=instance.input_data.list_of_thresholds,
        parameters=cpp_parameters,
        lb_travel_time=instance.get_lb_travel_time()
    )

    delays_on_arcs = get_delays_on_arcs(instance, congested_schedule)
    assert_schedule(model, congested_schedule, delays_on_arcs, instance)
    binaries = get_conflict_binaries(instance.conflicting_sets, instance.trip_routes, congested_schedule)
    total_delay = sum(sum(delays_on_arc_vehicle) for delays_on_arc_vehicle in delays_on_arcs)
    heuristic_solution = HeuristicSolution(congested_schedule=congested_schedule,
                                           delays_on_arcs=delays_on_arcs,
                                           binaries=binaries,
                                           total_delay=total_delay)

    return heuristic_solution


def set_heuristic_continuous_variables(model, heuristic_solution):
    for vehicle in model._departure:
        for position, arc in enumerate(model._departure[vehicle]):
            model.cbSetSolution(model._departure[vehicle][arc],
                                heuristic_solution.congested_schedule[vehicle][position])
            if isinstance(model._delay[vehicle][arc], grb.Var):
                model.cbSetSolution(model._delay[vehicle][arc], heuristic_solution.delays_on_arcs[vehicle][position])


def set_heuristic_binary_variables(model, heuristic_solution):
    for arc in model._gamma:
        for first_vehicle, second_vehicle in itertools.combinations(model._gamma[arc], 2):
            if heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle] != -1:
                if isinstance(model._alpha[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(model._alpha[arc][first_vehicle][second_vehicle],
                                        heuristic_solution.binaries.alpha[arc][first_vehicle][second_vehicle])
                if isinstance(model._beta[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(model._beta[arc][first_vehicle][second_vehicle],
                                        heuristic_solution.binaries.beta[arc][first_vehicle][second_vehicle])
                if isinstance(model._gamma[arc][first_vehicle][second_vehicle], grb.Var):
                    model.cbSetSolution(model._gamma[arc][first_vehicle][second_vehicle],
                                        heuristic_solution.binaries.gamma[arc][first_vehicle][second_vehicle])
            if heuristic_solution.binaries.gamma[arc][second_vehicle][first_vehicle] != -1:
                if isinstance(model._alpha[arc][second_vehicle][first_vehicle], grb.Var):
                    model.cbSetSolution(model._alpha[arc][second_vehicle][first_vehicle],
                                        heuristic_solution.binaries.alpha[arc][second_vehicle][first_vehicle])
                if isinstance(model._beta[arc][second_vehicle][first_vehicle], grb.Var):
                    model.cbSetSolution(model._beta[arc][second_vehicle][first_vehicle],
                                        heuristic_solution.binaries.beta[arc][second_vehicle][first_vehicle])
                if isinstance(model._gamma[arc][second_vehicle][first_vehicle], grb.Var):
                    model.cbSetSolution(model._gamma[arc][second_vehicle][first_vehicle],
                                        heuristic_solution.binaries.gamma[arc][second_vehicle][first_vehicle])


def suspend_procedure(heuristic_solution, model, instance) -> None:
    save_solution_in_external_file(heuristic_solution, instance)
    if model.cbGet(grb.GRB.Callback.MIP_OBJBND) > model._bestLowerBound:
        model._bestLowerBound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
    model.terminate()


def set_heuristic_solution(model: Model, heuristic_solution: HeuristicSolution, instance: Instance) -> None:
    solution_is_improving: bool = model._cbTotalDelay - heuristic_solution.total_delay > TOLERANCE
    if solution_is_improving:
        print("Setting heuristic solution in callback...", end=" ")
        set_heuristic_binary_variables(model, heuristic_solution)
        set_heuristic_continuous_variables(model, heuristic_solution)
        return_val_use_solution = model.cbUseSolution()
        print(f"Model.cbUseSolution() produced a solution with value {return_val_use_solution}")
        model.update()
        if return_val_use_solution == 1e+100:
            print("Heuristic solution has not been accepted - terminating MIP model")
            suspend_procedure(heuristic_solution, model, instance)


def callback(instance: Instance, status_quo: CompleteSolution, solver_params: SolverParameters) -> Callable:
    def call_local_search(model, where) -> None:
        if where == grb.GRB.Callback.MIP:
            get_current_bounds(model, instance.start_solution_time)
            update_remaining_time_for_optimization(model, instance, solver_params)

        if where == grb.GRB.Callback.MIPSOL:
            get_callback_solution(model, instance, status_quo)
            model._improvementClock = datetime.datetime.now().timestamp()
            model._bestUpperBound = model._cbTotalDelay

        if where == grb.GRB.Callback.MIPNODE:
            if model._flagUpdate:
                heuristic_solution = get_heuristic_solution(model, instance, solver_params)
                set_heuristic_solution(model, heuristic_solution, instance)

    return call_local_search
