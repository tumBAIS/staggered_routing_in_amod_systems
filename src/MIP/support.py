from __future__ import annotations

import collections
import datetime
import os
import pickle

from gurobipy import Model

from instanceModule.epochInstance import EpochInstance
from inputData import GUROBI_OPTIMALITY_GAP
from utils.classes import CompleteSolution, HeuristicSolution
from instanceModule.instance import Instance

pathToResults = os.path.join(os.path.dirname(__file__), "../../results")


def addOptimizationMeasuresToModel(model: Model):
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


def setGurobiParameters(model, instance):
    totalTimeRemaining = instance.inputData.algorithmTimeLimit - (
            datetime.datetime.now().timestamp() - instance.startSolutionTime)
    epochTimeRemaining = instance.inputData.epochTimeLimit - (
            datetime.datetime.now().timestamp() - instance.clockStartEpoch)
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


def initializeOptimizationMeasuresModel(model, statusQuo: CompleteSolution, instance):
    model._lowerBound.append(0)
    model._upperBound.append(statusQuo.totalDelay)
    timeSpentInOptimization = datetime.datetime.now().timestamp() - instance.startSolutionTime
    model._optimizationTime.append(timeSpentInOptimization)
    model._optimalityGap.append(100)
    model._numBigMConstraints = 0


def computeIISIfNotSolved(model: Model):
    if model.status in [3, 4, 5]:
        model.computeIIS()
        model.write(f"{pathToResults}/unsolvedModel.ilp")
        raise RuntimeError("Model could not be solved.")


def getRemainingTime(instance: Instance) -> float:
    return instance.inputData.algorithmTimeLimit - (
            datetime.datetime.now().timestamp() - instance.startSolutionTime)


def _deleteSolutionExternalFile(instance: Instance | EpochInstance) -> None:
    fileToDelete = f"{pathToResults}/initialSolution_{instance.clockStartEpoch}.p"
    if os.path.isfile(fileToDelete):
        os.remove(fileToDelete)
    return


def loadInitialSolution(instance: Instance | EpochInstance) -> HeuristicSolution:
    with open(f"{pathToResults}/initialSolution_{instance.clockStartEpoch}.p", "rb") as infile:
        initialSolution: HeuristicSolution = pickle.load(infile)
    _deleteSolutionExternalFile(instance)
    return initialSolution


def getFinalOptimizationMeasures(model, instance: Instance):
    if model.status not in [3, 4, 5]:
        model._lowerBound.append(model.ObjBound)
        model._upperBound.append(model.getObjective().getValue())
        timeSpentInOptimization = datetime.datetime.now().timestamp() - instance.startSolutionTime
        model._optimizationTime.append(timeSpentInOptimization)
        model._optimalityGap.append(model.MIPGap)
    return


def saveSolutionInExternalFile(heuristicSolution: HeuristicSolution | CompleteSolution,
                               instance: Instance | EpochInstance):
    pathToResults = os.path.join(os.path.dirname(__file__), "../../results")
    if not os.path.exists(pathToResults):
        os.makedirs(pathToResults,exist_ok=True)
    with open(f"{pathToResults}/initialSolution_{instance.clockStartEpoch}.p", "wb") as outfile:
        pickle.dump(heuristicSolution, outfile)
        print("saved heuristic solution in external file")
