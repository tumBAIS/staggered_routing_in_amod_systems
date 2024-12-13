from __future__ import annotations
import datetime
from pathlib import Path
import gurobipy as grb
from typing import Optional
from utils.tools import SuppressOutput

from MIP import StaggeredRoutingModel
from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP, TOLERANCE
from instance_module.epoch_instance import EpochInstance
from utils.classes import Solution, HeuristicSolution
from MIP.support import (
    set_gurobi_parameters,
    compute_iis_if_not_solved,
    load_initial_solution,
    get_final_optimization_measures,
    save_solution_in_external_file,
    OptimizationMeasures
)
from MIP.integer_variables import add_conflict_variables
from MIP.continuous_variables import add_continuous_variables
from MIP.constraints import add_conflict_constraints
from MIP.callback import callback
from MIP.warm_start import set_warm_start_model

# Define the path for temporary files
path_to_temp = Path(__file__).parent.parent.parent / "temp"


def construct_model(
        instance: EpochInstance,
        status_quo: Solution,
        epoch_warm_start: Solution,
        solver_params: SolverParameters,
) -> StaggeredRoutingModel:
    """
    Construct and initialize the optimization model.

    Args:
        instance: The problem instance containing trip and arc data.
        status_quo: The current solution state.
        epoch_warm_start: A warm start solution for the epoch.
        solver_params: Parameters controlling solver behavior.

    Returns:
        StaggeredRoutingModel: The constructed optimization model.
    """
    print("\n" + "=" * 50)
    print(f"Constructing Optimization Model For Epoch {instance.epoch_id}".center(50))
    print("=" * 50)

    # Initialize the model with relevant parameters
    print("Initializing the optimization model...")
    model = StaggeredRoutingModel(status_quo.total_delay, solver_params, instance.start_solution_time)
    print("Model initialized successfully.")

    # Check optimization and time constraints
    print("Checking optimization and time constraints...")
    if not solver_params.optimize:
        print("Optimization flag is disabled. Skipping model construction.")
        model.set_optimize_flag(False)
        return model

    if not is_there_remaining_time(instance, solver_params):
        print("No remaining time for optimization. Model will not be constructed.")
        model.set_optimize_flag(False)
        return model

    print("Optimization and time constraints validated.")

    # Add variables and constraints to the model
    add_conflict_variables(model, instance)
    print("Conflict variables added.")

    add_continuous_variables(model, instance, status_quo, epoch_warm_start)
    print("Continuous variables added.")

    add_conflict_constraints(model, instance)
    print("Conflict constraints added.")
    model.print_num_big_m_constraints()

    model.add_travel_continuity_constraints(instance)
    print("Travel continuity constraints added.")

    model.add_objective_function()
    print("Objective function added.")

    print("=" * 50)
    print("Model construction completed successfully.".center(50))
    print("=" * 50)

    return model


def _continue_solving(model: StaggeredRoutingModel, instance: EpochInstance, solver_params: SolverParameters) -> bool:
    """Determines whether the optimization should continue."""
    has_significant_gap = model.get_last_optimality_gap() > GUROBI_OPTIMALITY_GAP + TOLERANCE
    model_is_feasible = model.status not in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED,
                                             grb.GRB.Status.INTERRUPTED]
    model_time_limit_not_reached = model.status != grb.GRB.Status.TIME_LIMIT

    return (
            has_significant_gap
            and is_there_remaining_time(instance, solver_params)
            and model_is_feasible
            and model_time_limit_not_reached
    )


def is_there_remaining_time(instance: EpochInstance, solver_params: SolverParameters) -> bool:
    """Checks if there is enough remaining time to continue optimization."""
    total_remaining_time = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_remaining_time = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    return min(total_remaining_time, epoch_remaining_time) > 0


def run_model(
        model: StaggeredRoutingModel,
        instance: EpochInstance,
        warm_start: HeuristicSolution | Solution,
        status_quo: Solution,
        solver_params: SolverParameters,
) -> Optional[OptimizationMeasures]:
    """Runs the optimization model with the specified parameters."""
    if not model.get_optimize_flag() or not is_there_remaining_time(instance,
                                                                    solver_params) or instance.instance_params.staggering_cap == 0:
        return None

    # Save the initial solution for reference
    save_solution_in_external_file(warm_start, instance)

    # Run optimization until criteria are met
    while _continue_solving(model, instance, solver_params):
        try:
            initial_solution = load_initial_solution(instance)
        except FileNotFoundError:
            print("No solution to start the model - terminating procedure.")
            return None

        # Set the warm start if applicable
        if solver_params.warm_start:
            set_warm_start_model(model, initial_solution, instance)

        # Configure Gurobi parameters
        set_gurobi_parameters(model, instance, solver_params)

        # Optimize with or without a callback
        if solver_params.local_search_callback:
            model.optimize(callback(instance, status_quo, solver_params))
        else:
            model.optimize()

        # fetch final optimization measures
        return get_final_optimization_measures(model, instance)

    # Compute IIS if the model was not solved successfully
    compute_iis_if_not_solved(model)
    return None
