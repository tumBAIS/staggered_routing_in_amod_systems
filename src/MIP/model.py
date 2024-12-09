from __future__ import annotations
import datetime

import MIP.support
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
from pathlib import Path

path_to_temp = Path(__file__).parent.parent.parent / "temp"


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


def run_model(
        model: Model,
        instance: Instance | EpochInstance,
        warmStart: CompleteSolution | HeuristicSolution | EpochSolution,
        statusQuo: CompleteSolution | EpochSolution,
        solver_params: SolverParameters,
) -> MIP.support.OptimizationMeasures:
    """
    Runs the optimization model with given parameters, handling warm starts and callbacks.
    """
    optimization_measures = None
    # Check if optimization should proceed
    if not model._optimize or not is_there_remaining_time(instance,
                                                          solver_params) or instance.input_data.staggering_cap == 0:
        return

    # Save the initial solution for reference
    save_solution_in_external_file(warmStart, instance)

    # Continue solving while criteria are met
    while _continue_solving(model, instance, solver_params):
        try:
            # Load the initial solution
            initialSolution = load_initial_solution(instance)
        except Exception as e:
            print("No solution to start the model - terminating procedure")
            return

        # Set up the warm start if required
        if solver_params.warm_start:
            set_warm_start_model(model, initialSolution)

        # Configure solver parameters
        set_gurobi_parameters(model, instance, solver_params)

        # Run the optimization with or without a local search callback
        if solver_params.local_search_callback:
            model.optimize(callback(instance, statusQuo, solver_params))
        else:
            model.optimize()

        # Try to obtain final optimization measures
        try:
            optimization_measures = get_final_optimization_measures(model, instance)
        except Exception as e:
            print("Not possible to obtain final optimization measures")

    # Compute an IIS if the model was not solved successfully
    compute_iis_if_not_solved(model)
    return optimization_measures
