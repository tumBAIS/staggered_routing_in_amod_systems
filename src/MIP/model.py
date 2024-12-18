from __future__ import annotations
import datetime
from pathlib import Path
import gurobipy as grb
from typing import Optional
import cpp_module as cpp
from MIP import StaggeredRoutingModel
from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP, TOLERANCE
from problem.epoch_instance import EpochInstance
from problem.solution import Solution, HeuristicSolution
from MIP.support import (
    set_gurobi_parameters,
    compute_iis_if_not_solved
)
from MIP.integer_variables import add_conflict_variables
from MIP.continuous_variables import add_continuous_variables
from MIP.constraints import add_conflict_constraints
from MIP.callback import callback
from MIP.warm_start import set_warm_start_model
from utils.aliases import OptimizationMeasures

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
    print(f"Constructing Optimization Model Epoch {instance.epoch_id}".center(50))
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


def run_model(model: StaggeredRoutingModel,
              instance: EpochInstance,
              warm_start: HeuristicSolution | Solution,
              solver_params: SolverParameters,
              cpp_local_search: cpp.cpp_local_search) -> Optional[OptimizationMeasures]:
    """Runs the optimization model with the specified parameters."""
    print("=" * 50)
    print("Starting Model Optimization".center(50))
    print("=" * 50)

    # Check if model should be optimized
    if (not model.get_optimize_flag() or
            not is_there_remaining_time(instance, solver_params) or
            instance.instance_params.staggering_cap == 0):
        print("Optimization skipped due to one of the following reasons:")
        print(" - Optimization flag is disabled.")
        print(" - No remaining time for optimization.")
        print(" - Staggering capacity is zero.")
        print("=" * 50)
        return None

    set_gurobi_parameters(model, instance, solver_params)

    if solver_params.warm_start:
        print("Applying warm start to the model...")
        set_warm_start_model(model, warm_start, instance)

    # Optimize the model
    print("Optimizing the model...")
    if solver_params.local_search_callback:
        print("Using local search callback during optimization.")
        model.optimize(callback(instance, solver_params, cpp_local_search))
    else:
        model.optimize()

    # Handle infeasible or interrupted cases
    if model.status in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED]:
        print("Optimization was unsuccessful. Computing IIS...")
        compute_iis_if_not_solved(model)
        raise RuntimeError("Model could not be solved")

    print("Optimization completed successfully.")
    print("=" * 50)

    if model.status not in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED, grb.GRB.Status.INTERRUPTED]:
        return model.get_final_optimization_metrics(instance.start_solution_time)
    return None
