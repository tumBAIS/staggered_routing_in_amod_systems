from congestionModel.core import getFreeFlowSchedule, \
    getTotalTravelTime, getStaggeringApplicable
from instanceModule.epochInstance import EpochInstance
from utils.classes import EpochSolution
from gurobipy import Model
import gurobipy as grb


def _getModelReleaseTimes(model: Model, paths: list[list[int]]) -> list[float]:
    return [model._departure[vehicle][path[0]].X for vehicle, path in enumerate(paths)]


def _getModelSchedule(model: Model, paths: list[list[int]]) -> list[list[float]]:
    return [[model._departure[vehicle][arc].X for arc in path] for vehicle, path in enumerate(paths)]


def _getModelDelayOnArcs(model: Model, paths: list[list[int]]) -> list[list[float]]:
    return [[model._delay[vehicle][arc].X if isinstance(model._delay[vehicle][arc], grb.Var) else 0 for arc in path] for
            vehicle, path in enumerate(paths)]


def _getStaggeringApplied(releaseTimesSolution, releaseTimesStatusQuo):
    return [releaseTimesSolution[i] - releaseTimesStatusQuo[i] for i in range(len(releaseTimesStatusQuo))]


def getEpochModelSolution(model: Model, epochInstance: EpochInstance, epochStatusQuo: EpochSolution,
                          epochWarmStart: EpochSolution) -> EpochSolution:
    if not epochInstance.inputData.optimize or not model._optimize:
        if not epochInstance.inputData.warm_start:
            return epochStatusQuo
        return epochWarmStart

    totalDelay = model._totalDelay.X
    releaseTimes = _getModelReleaseTimes(model, epochInstance.trip_routes)
    congestedSchedule = _getModelSchedule(model, epochInstance.trip_routes)
    delaysOnArcs = _getModelDelayOnArcs(model, epochInstance.trip_routes)
    freeFlowSchedule = getFreeFlowSchedule(epochInstance, congestedSchedule)
    staggeringApplied = _getStaggeringApplied(releaseTimes, epochStatusQuo.releaseTimes)
    slack = getStaggeringApplicable(epochInstance, staggeringApplied)
    totalTravelTime = getTotalTravelTime(congestedSchedule)

    modelSolution = EpochSolution(delaysOnArcs=delaysOnArcs,
                                  freeFlowSchedule=freeFlowSchedule,
                                  releaseTimes=releaseTimes,
                                  staggeringApplicable=slack,
                                  totalDelay=totalDelay,
                                  congestedSchedule=congestedSchedule,
                                  staggeringApplied=staggeringApplied,
                                  vehiclesUtilizingArcs=epochStatusQuo.vehiclesUtilizingArcs,
                                  totalTravelTime=totalTravelTime)

    return modelSolution
