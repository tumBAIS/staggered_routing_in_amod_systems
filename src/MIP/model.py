from __future__ import annotations

import datetime
import os

from MIP.support import addOptimizationMeasuresToModel, setGurobiParameters, \
    initializeOptimizationMeasuresModel, computeIISIfNotSolved, loadInitialSolution, \
    getFinalOptimizationMeasures, saveSolutionInExternalFile
from MIP.integerVariables import addConflictVariables
from MIP.continuousVariables import addContinuousVariables
from MIP.constraints import addConflictConstraints, addTravelContinuityConstraints, \
    addObjectiveFunction
from MIP.callback import callback
from MIP.warmStart import setWarmStartModel
from instanceModule.instance import Instance
from gurobipy import Model
import gurobipy as grb
from inputData import GUROBI_OPTIMALITY_GAP, TOLERANCE
from utils.classes import EpochSolution, CompleteSolution, HeuristicSolution
from instanceModule.epochInstance import EpochInstance

pathToResults = os.path.join(os.path.dirname(__file__), "../../results")


def constructModel(instance: Instance | EpochInstance, statusQuo: CompleteSolution | EpochSolution,
                   epochWarmStart) -> Model:
    model = grb.Model("staggeringRoutingModel")  # create gurobi model
    model._optimize = True
    if not instance.inputData.optimize or not isThereRemainingTime(instance):
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
    addObjectiveFunction(instance.inputData, model)
    return model


def _continueSolving(model, instance) -> bool:
    isThereGap = model._optimalityGap[-1] > GUROBI_OPTIMALITY_GAP + TOLERANCE
    modelIsFeasibleAndBounded = model.status not in [3, 4, 5]
    modelDidNotRunOutOfTime = model.status != grb.GRB.Status.TIME_LIMIT
    return isThereGap and isThereRemainingTime(instance) and modelIsFeasibleAndBounded and modelDidNotRunOutOfTime


def isThereRemainingTime(instance):
    totalTimeRemaining = instance.inputData.algorithmTimeLimit - (
            datetime.datetime.now().timestamp() - instance.startSolutionTime)
    epochTimeRemaining = instance.inputData.epochTimeLimit - (
            datetime.datetime.now().timestamp() - instance.clockStartEpoch)
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
        if instance.inputData.warmStart:
            setWarmStartModel(model, initialSolution)
        setGurobiParameters(model, instance)
        if instance.inputData.callLocalSearch:
            model.optimize(callback(instance, statusQuo))
        else:
            model.optimize()
        try:
            getFinalOptimizationMeasures(model, instance)
        except:
            print("not possible to obtain final optimization measures")
    computeIISIfNotSolved(model)
    model.write(f"{pathToResults}/model.lp")
