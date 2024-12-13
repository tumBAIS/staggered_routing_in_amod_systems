from __future__ import annotations

import os
import pickle
import datetime
import dataclasses
from utils.tools import SuppressOutput

import gurobipy as grb
from typing import Optional

from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP
from instance_module.epoch_instance import EpochInstance
from utils.classes import Solution, HeuristicSolution
from MIP import StaggeredRoutingModel

# Define the path for results
path_to_results = os.path.join(os.path.dirname(__file__), "../../results")


@dataclasses.dataclass
class OptimizationMeasures:
    lower_bound_list: list[float]
    upper_bound_list: list[float]
    optimality_gap_list: list[float]


def set_gurobi_parameters(model: StaggeredRoutingModel, instance: EpochInstance,
                          solver_params: SolverParameters) -> None:
    """Set Gurobi solver parameters based on time and optimization settings."""
    total_time_remaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time
    )
    epoch_time_remaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch
    )
    time_remaining = max(0.0, round(min(total_time_remaining, epoch_time_remaining), 2))
    # Suppress Gurobi logging
    log_val = 1 if solver_params.verbose_model else 0
    with SuppressOutput():
        model.setParam('OutputFlag', log_val)
        model.setParam("timeLimit", time_remaining)
        model.setParam("MIPGap", GUROBI_OPTIMALITY_GAP * 0.01)
        model.setParam("NodeFileStart", 0.5)
        model.setParam("Threads", 1)
        model.setParam("MIPFocus", 2)
        model.setParam("Disconnected", 0)
        model.setParam("NumericFocus", 2)


def compute_iis_if_not_solved(model: StaggeredRoutingModel) -> None:
    """Compute IIS if the model is infeasible, unbounded, or otherwise not solved."""
    model.computeIIS()
    model.write(f"{path_to_results}/unsolvedModel.ilp")
    raise RuntimeError("Model could not be solved.")


def _delete_solution_external_file(instance: EpochInstance) -> None:
    """Delete the external file storing the initial solution."""
    file_to_delete = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    if os.path.isfile(file_to_delete):
        os.remove(file_to_delete)


def load_initial_solution(instance: EpochInstance) -> HeuristicSolution:
    """Load the initial solution from an external file."""
    file_path = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    with open(file_path, "rb") as infile:
        initial_solution: HeuristicSolution = pickle.load(infile)
    _delete_solution_external_file(instance)
    return initial_solution


def get_final_optimization_measures(model: StaggeredRoutingModel, instance: EpochInstance) -> (
        Optional)[OptimizationMeasures]:
    """Retrieve final optimization measures if the model was successfully solved."""
    if model.status not in [grb.GRB.Status.INFEASIBLE, grb.GRB.Status.UNBOUNDED, grb.GRB.Status.INTERRUPTED]:
        model.store_lower_bound()
        model.store_upper_bound()
        model.store_optimality_gap()
        model.store_optimization_time(instance.start_solution_time)

        return OptimizationMeasures(
            lower_bound_list=model.get_lower_bound_list(),
            upper_bound_list=model.get_upper_bound_list(),
            optimality_gap_list=model.get_optimality_gap_list(),
        )
    return None


def save_solution_in_external_file(solution: HeuristicSolution | Solution,
                                   instance: EpochInstance) -> None:
    """Save the heuristic solution to an external file."""
    os.makedirs(path_to_results, exist_ok=True)
    file_path = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    with open(file_path, "wb") as outfile:
        pickle.dump(solution, outfile)
        print("Saved heuristic solution in external file.")
