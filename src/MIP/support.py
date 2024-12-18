from __future__ import annotations

import os
import datetime
from utils.tools import SuppressOutput
from input_data import SolverParameters, GUROBI_OPTIMALITY_GAP
from problem.epoch_instance import EpochInstance
from MIP import StaggeredRoutingModel

# Define the path for results
path_to_results = os.path.join(os.path.dirname(__file__), "../../results")


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
