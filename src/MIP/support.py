from __future__ import annotations

import os
import pickle
import datetime
import dataclasses
import gurobipy as grb
from typing import Optional

from gurobipy import Model
from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP
from instance_module.epoch_instance import EpochInstance
from instance_module.instance import Instance
from utils.classes import CompleteSolution, HeuristicSolution

# Define the path for results
path_to_results = os.path.join(os.path.dirname(__file__), "../../results")


@dataclasses.dataclass
class OptimizationMeasures:
    lower_bound_list: list[float]
    upper_bound_list: list[float]
    optimality_gap_list: list[float]


def add_optimization_measures_to_model(model: Model) -> None:
    """Add containers for optimization metrics to the model."""
    model._optimalityGap = []
    model._lowerBound = []
    model._upperBound = []
    model._optimizationTime = []
    model._flagUpdate = False
    model._bestLowerBound = 0
    model._bestUpperBound = float("inf")
    model._improvementClock = datetime.datetime.now().timestamp()


def set_gurobi_parameters(model: Model, instance: Instance | EpochInstance, solver_params: SolverParameters) -> None:
    """Set Gurobi solver parameters based on time and optimization settings."""
    total_time_remaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_time_remaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    time_remaining = max(0.0, round(min(total_time_remaining, epoch_time_remaining), 2))

    model.setParam("timeLimit", time_remaining)
    model.setParam("MIPGap", GUROBI_OPTIMALITY_GAP * 0.01)
    model.setParam("NodeFileStart", 0.5)
    model.setParam("Threads", 1)
    model.setParam("MIPFocus", 2)
    model.setParam("Disconnected", 0)
    model.setParam("NumericFocus", 2)
    model.setParam("FeasibilityTol", 1e-8)
    model.setParam("IntFeasTol", 1e-7)


def initialize_optimization_measures_model(model: Model, status_quo: CompleteSolution,
                                           instance: Instance | EpochInstance) -> None:
    """Initialize model with default optimization measures."""
    model._lowerBound.append(0)
    model._upperBound.append(status_quo.total_delay)
    model._optimizationTime.append(datetime.datetime.now().timestamp() - instance.start_solution_time)
    model._optimalityGap.append(100)
    model._numBigMConstraints = 0


def compute_iis_if_not_solved(model: Model) -> None:
    """Compute IIS if the model is infeasible, unbounded, or otherwise not solved."""
    if model.status in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED, grb.GRB.Status.INTERRUPTED]:
        model.computeIIS()
        model.write(f"{path_to_results}/unsolvedModel.ilp")
        raise RuntimeError("Model could not be solved.")


def _delete_solution_external_file(instance: Instance | EpochInstance) -> None:
    """Delete the external file storing the initial solution."""
    file_to_delete = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    if os.path.isfile(file_to_delete):
        os.remove(file_to_delete)


def load_initial_solution(instance: Instance | EpochInstance) -> HeuristicSolution:
    """Load the initial solution from an external file."""
    file_path = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    with open(file_path, "rb") as infile:
        initial_solution: HeuristicSolution = pickle.load(infile)
    _delete_solution_external_file(instance)
    return initial_solution


def get_final_optimization_measures(model: Model, instance: Instance | EpochInstance) -> Optional[OptimizationMeasures]:
    """Retrieve final optimization measures if the model was successfully solved."""
    if model.status not in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED, grb.GRB.Status.INTERRUPTED]:
        model._lowerBound.append(round(model.ObjBound, 2))
        model._upperBound.append(round(model.getObjective().getValue(), 2))
        model._optimizationTime.append(datetime.datetime.now().timestamp() - instance.start_solution_time)
        model._optimalityGap.append(round(model.MIPGap * 100, 2))

        return OptimizationMeasures(
            lower_bound_list=model._lowerBound,
            upper_bound_list=model._upperBound,
            optimality_gap_list=model._optimalityGap,
        )
    return None


def save_solution_in_external_file(solution: HeuristicSolution | CompleteSolution,
                                   instance: Instance | EpochInstance) -> None:
    """Save the heuristic solution to an external file."""
    os.makedirs(path_to_results, exist_ok=True)
    file_path = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    with open(file_path, "wb") as outfile:
        pickle.dump(solution, outfile)
        print("Saved heuristic solution in external file.")
