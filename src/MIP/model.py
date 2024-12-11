from __future__ import annotations
import datetime
from pathlib import Path

from gurobipy import Model
import gurobipy as grb

from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP, TOLERANCE
from instance_module.instance import Instance
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution, CompleteSolution, HeuristicSolution
from MIP.support import (
    add_optimization_measures_to_model,
    set_gurobi_parameters,
    initialize_optimization_measures_model,
    compute_iis_if_not_solved,
    load_initial_solution,
    get_final_optimization_measures,
    save_solution_in_external_file,
    OptimizationMeasures
)
from MIP.integer_variables import add_conflict_variables
from MIP.continuous_variables import add_continuous_variables
from MIP.constraints import add_conflict_constraints, add_travel_continuity_constraints, add_objective_function
from MIP.callback import callback
from MIP.warm_start import set_warm_start_model

# Define the path for temporary files
path_to_temp = Path(__file__).parent.parent.parent / "temp"


def construct_model(
        instance: Instance | EpochInstance,
        status_quo: CompleteSolution | EpochSolution,
        epoch_warm_start,
        solver_params: SolverParameters,
) -> Model:
    """Constructs and initializes the optimization model."""
    model = grb.Model("staggered_routing")
    model._optimize = True

    if not solver_params.optimize or not is_there_remaining_time(instance, solver_params):
        model._optimize = False
        if not is_there_remaining_time(instance, solver_params):
            print("No remaining time for optimization - model will not be constructed.")
        return model

    add_optimization_measures_to_model(model)
    initialize_optimization_measures_model(model, status_quo, instance)
    add_conflict_variables(model, instance)
    add_continuous_variables(model, instance, status_quo, epoch_warm_start)
    add_conflict_constraints(model, instance)
    add_travel_continuity_constraints(model, instance)
    add_objective_function(model)

    return model


def _continue_solving(model: Model, instance: Instance, solver_params: SolverParameters) -> bool:
    """Determines whether the optimization should continue."""
    has_significant_gap = model._optimalityGap[-1] > GUROBI_OPTIMALITY_GAP + TOLERANCE
    model_is_feasible = model.status not in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED,
                                             grb.GRB.Status.INTERRUPTED]
    model_time_limit_not_reached = model.status != grb.GRB.Status.TIME_LIMIT

    return (
            has_significant_gap
            and is_there_remaining_time(instance, solver_params)
            and model_is_feasible
            and model_time_limit_not_reached
    )


def is_there_remaining_time(instance, solver_params: SolverParameters) -> bool:
    """Checks if there is enough remaining time to continue optimization."""
    total_remaining_time = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_remaining_time = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    return min(total_remaining_time, epoch_remaining_time) > 0


def run_model(
        model: Model,
        instance: Instance | EpochInstance,
        warm_start: CompleteSolution | HeuristicSolution | EpochSolution,
        status_quo: CompleteSolution | EpochSolution,
        solver_params: SolverParameters,
) -> OptimizationMeasures:
    """Runs the optimization model with the specified parameters."""
    if not model._optimize or not is_there_remaining_time(instance,
                                                          solver_params) or instance.input_data.staggering_cap == 0:
        return None

    # Save the initial solution for reference
    save_solution_in_external_file(warm_start, instance)

    # Run optimization until criteria are met
    while _continue_solving(model, instance, solver_params):
        try:
            initial_solution = load_initial_solution(instance)
        except Exception as e:
            print("No solution to start the model - terminating procedure.")
            return None

        # Set the warm start if applicable
        if solver_params.warm_start:
            set_warm_start_model(model, initial_solution)

        # Configure Gurobi parameters
        set_gurobi_parameters(model, instance, solver_params)

        # Optimize with or without a callback
        if solver_params.local_search_callback:
            model.optimize(callback(instance, status_quo, solver_params))
        else:
            model.optimize()

        # Try to fetch final optimization measures
        try:
            return get_final_optimization_measures(model, instance)
        except Exception as e:
            print("Unable to obtain final optimization measures.")

    # Compute IIS if the model was not solved successfully
    compute_iis_if_not_solved(model)
    return None
