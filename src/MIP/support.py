from __future__ import annotations

import dataclasses
import datetime
import os
import pickle

from gurobipy import Model

from input_data import SolverParameters
from instance_module.epoch_instance import EpochInstance
from input_data import GUROBI_OPTIMALITY_GAP
from utils.classes import CompleteSolution, HeuristicSolution
from instance_module.instance import Instance
from typing import Optional

path_to_results = os.path.join(os.path.dirname(__file__), "../../results")


@dataclasses.dataclass
class OptimizationMeasures:
    lower_bound_list: list[float]
    upper_bound_list: list[float]
    optimality_gap_list: list[float]


def add_optimization_measures_to_model(model: Model):
    """Save local search heuristic solution info"""
    model._optimalityGap = []
    model._lowerBound = []
    model._upperBound = []
    model._optimizationTime = []
    model._flagUpdate = False
    model._bestLowerBound = 0
    model._bestUpperBound = float("inf")
    model._improvementClock = datetime.datetime.now().timestamp()

    return


def set_gurobi_parameters(model, instance, solver_params: SolverParameters):
    totalTimeRemaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time)
    epochTimeRemaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch)
    timeRemaining = min(totalTimeRemaining, epochTimeRemaining)
    model.setParam("timeLimit", max(0.0, round(timeRemaining, 2)))
    model.setParam("MIPGap", (GUROBI_OPTIMALITY_GAP * 0.01))
    model.setParam("NodeFileStart", 0.5)  # helps to solve larger instances
    model.setParam("Threads", 1)  # helps to solve larger instances
    model.setParam("MIPFocus", 2)
    model.setParam("Disconnected", 0)
    model.setParam("NumericFocus", 2)
    model.setParam("FeasibilityTol", 1e-8)
    model.setParam("IntFeasTol", 1e-7)
    return


def initialize_optimization_measures_model(model, statusQuo: CompleteSolution, instance):
    model._lowerBound.append(0)
    model._upperBound.append(statusQuo.total_delay)
    timeSpentInOptimization = datetime.datetime.now().timestamp() - instance.start_solution_time
    model._optimizationTime.append(timeSpentInOptimization)
    model._optimalityGap.append(100)
    model._numBigMConstraints = 0


def compute_iis_if_not_solved(model: Model):
    if model.status in [3, 4, 5]:
        model.computeIIS()
        model.write(f"{path_to_results}/unsolvedModel.ilp")
        raise RuntimeError("Model could not be solved.")


def _delete_solution_external_file(instance: Instance | EpochInstance) -> None:
    fileToDelete = f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p"
    if os.path.isfile(fileToDelete):
        os.remove(fileToDelete)
    return


def load_initial_solution(instance: Instance | EpochInstance) -> HeuristicSolution:
    with open(f"{path_to_results}/initialSolution_{instance.clock_start_epoch}.p", "rb") as infile:
        initialSolution: HeuristicSolution = pickle.load(infile)
    _delete_solution_external_file(instance)
    return initialSolution


def get_final_optimization_measures(model, instance: Instance) -> Optional[OptimizationMeasures]:
    if model.status not in [3, 4, 5]:
        model._lowerBound.append(round(model.ObjBound, 2))
        model._upperBound.append(round(model.getObjective().getValue(), 2))
        timeSpentInOptimization = datetime.datetime.now().timestamp() - instance.start_solution_time
        model._optimizationTime.append(timeSpentInOptimization)
        model._optimalityGap.append(round(model.MIPGap * 100, 2))
        return OptimizationMeasures(lower_bound_list=model._lowerBound,
                                    upper_bound_list=model._upperBound,
                                    optimality_gap_list=model._optimalityGap)


def save_solution_in_external_file(heuristicSolution: HeuristicSolution | CompleteSolution,
                                   instance: Instance | EpochInstance):
    pathToResults = os.path.join(os.path.dirname(__file__), "../../results")
    if not os.path.exists(pathToResults):
        os.makedirs(pathToResults, exist_ok=True)
    with open(f"{pathToResults}/initialSolution_{instance.clock_start_epoch}.p", "wb") as outfile:
        pickle.dump(heuristicSolution, outfile)
        print("saved heuristic solution in external file")
