from __future__ import annotations

import datetime
import os

from input_data import SolverParameters
from MIP.support import add_optimization_measures_to_model, set_gurobi_parameters, \
    initialize_optimization_measures_model, compute_iis_if_not_solved, load_initial_solution, \
    get_final_optimization_measures, save_solution_in_external_file
from MIP.integer_variables import add_conflict_variables
from MIP.continuous_variables import add_continuous_variables
from MIP.constraints import add_conflict_constraints, add_travel_continuity_constraints, \
    add_objective_function
from MIP.callback import callback
from MIP.warm_start import set_warm_start_model
from instance_module.instance import Instance
from gurobipy import Model
import gurobipy as grb
from input_data import GUROBI_OPTIMALITY_GAP, TOLERANCE
from utils.classes import EpochSolution, CompleteSolution, HeuristicSolution
from instance_module.epoch_instance import EpochInstance

path_to_results = os.path.join(os.path.dirname(__file__), "../../results")


def construct_model(instance: Instance | EpochInstance, statusQuo: CompleteSolution | EpochSolution,
                    epochWarmStart, solver_params: SolverParameters) -> Model:
    model = grb.Model("staggeringRoutingModel")  # create gurobi model
    model._optimize = True
    if not solver_params.optimize or not is_there_remaining_time(instance, solver_params):
        model._optimize = False
        if not is_there_remaining_time(instance, solver_params):
            print("no remaining time for optimization - model will not be constructed")
        return model
    add_optimization_measures_to_model(model)
    initialize_optimization_measures_model(model, statusQuo, instance)
    add_conflict_variables(model, instance)
    add_continuous_variables(model, instance, statusQuo, epochWarmStart)
    add_conflict_constraints(model, instance)
    add_travel_continuity_constraints(model, instance)
    add_objective_function(model)
    return model


def _continue_solving(model, instance, solver_params: SolverParameters) -> bool:
    isThereGap = model._optimalityGap[-1] > GUROBI_OPTIMALITY_GAP + TOLERANCE
    modelIsFeasibleAndBounded = model.status not in [3, 4, 5]
    modelDidNotRunOutOfTime = model.status != grb.GRB.Status.TIME_LIMIT
    return isThereGap and is_there_remaining_time(instance,
                                                  solver_params) and modelIsFeasibleAndBounded and modelDidNotRunOutOfTime


def is_there_remaining_time(instance, solver_params: SolverParameters):
    totalTimeRemaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time)
    epochTimeRemaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch)
    timeRemaining = min(epochTimeRemaining, totalTimeRemaining)
    return timeRemaining > 0


def run_model(model: Model,
              instance: Instance | EpochInstance,
              warmStart: CompleteSolution | HeuristicSolution | EpochSolution,
              statusQuo: CompleteSolution | EpochSolution,
              solver_params: SolverParameters):
    if not model._optimize or not is_there_remaining_time(instance, solver_params):
        return
    save_solution_in_external_file(warmStart, instance)
    while _continue_solving(model, instance, solver_params):
        try:
            initialSolution = load_initial_solution(instance)
        except:
            print("no solution to start the model - terminating procedure")
            return
        if solver_params.warm_start:
            set_warm_start_model(model, initialSolution)
        set_gurobi_parameters(model, instance, solver_params)
        if solver_params.local_search_callback:
            model.optimize(callback(instance, statusQuo, solver_params))
        else:
            model.optimize()
        try:
            get_final_optimization_measures(model, instance)
        except:
            print("not possible to obtain final optimization measures")
    compute_iis_if_not_solved(model)
    model.write(f"{path_to_results}/model.lp")
