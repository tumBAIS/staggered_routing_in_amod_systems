from __future__ import annotations

import datetime
import os

from MIP.support import addOptimizationMeasuresToModel, setGurobiParameters, \
    initializeOptimizationMeasuresModel, computeIISIfNotSolved, loadInitialSolution, \
    getFinalOptimizationMeasures, saveSolutionInExternalFile
from MIP.integer_variables import addConflictVariables
from MIP.continuous_variables import addContinuousVariables
from MIP.constraints import addConflictConstraints, addTravelContinuityConstraints, \
    addObjectiveFunction
from MIP.callback import callback
from MIP.warm_start import setWarmStartModel
from instanceModule.instance import Instance
from gurobipy import Model
import gurobipy as grb
from input_data import GUROBI_OPTIMALITY_GAP, TOLERANCE
from utils.classes import EpochSolution, CompleteSolution, HeuristicSolution
from instanceModule.epoch_instance import EpochInstance

pathToResults = os.path.join(os.path.dirname(__file__), "../../results")


def constructModel(instance: Instance | EpochInstance, statusQuo: CompleteSolution | EpochSolution,
                   epochWarmStart) -> Model:
    model = grb.Model("staggeringRoutingModel")  # create gurobi model
    model._optimize = True
    if not instance.input_data.optimize or not isThereRemainingTime(instance):
        model._optimize = False
        if not isThereRemainingTime(instance):
            print("no remaining time for optimization - model will not be constructed")
        return model
    addOptimizationMeasuresToModel(model)
    initializeOptimizationMeasuresModel(model, statusQuo, instance)
    addConflictVariables(model, instance)
    addContinuousVariables(model, instance, statusQuo, epochWarmStart)
    addConflictConstraints(model, instance)
    addTravelContinuityConstraints(model, instance)
    addObjectiveFunction(instance.input_data, model)
    return model


def _continueSolving(model, instance) -> bool:
    isThereGap = model._optimalityGap[-1] > GUROBI_OPTIMALITY_GAP + TOLERANCE
    modelIsFeasibleAndBounded = model.status not in [3, 4, 5]
    modelDidNotRunOutOfTime = model.status != grb.GRB.Status.TIME_LIMIT
    return isThereGap and isThereRemainingTime(instance) and modelIsFeasibleAndBounded and modelDidNotRunOutOfTime


def isThereRemainingTime(instance):
    totalTimeRemaining = instance.input_data.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time)
    epochTimeRemaining = instance.input_data.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch)
    timeRemaining = min(epochTimeRemaining, totalTimeRemaining)
    return timeRemaining > 0


def runModel(model: Model,
             instance: Instance | EpochInstance,
             warmStart: CompleteSolution | HeuristicSolution | EpochSolution,
             statusQuo: CompleteSolution | EpochSolution):
    if not model._optimize or not isThereRemainingTime(instance):
        return
    saveSolutionInExternalFile(warmStart, instance)
    while _continueSolving(model, instance):
        try:
            initialSolution = loadInitialSolution(instance)
        except:
            print("no solution to start the model - terminating procedure")
            return
        if instance.input_data.warm_start:
            setWarmStartModel(model, initialSolution)
        setGurobiParameters(model, instance)
        if instance.input_data.call_local_search:
            model.optimize(callback(instance, statusQuo))
        else:
            model.optimize()
        try:
            getFinalOptimizationMeasures(model, instance)
        except:
            print("not possible to obtain final optimization measures")
    computeIISIfNotSolved(model)
    model.write(f"{pathToResults}/model.lp")
