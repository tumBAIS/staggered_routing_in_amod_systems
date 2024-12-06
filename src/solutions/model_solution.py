from congestion_model.core import get_free_flow_schedule, \
    get_total_travel_time, get_staggering_applicable
from instanceModule.epoch_instance import EpochInstance
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
    if not epochInstance.input_data.optimize or not model._optimize:
        if not epochInstance.input_data.warm_start:
            return epochStatusQuo
        return epochWarmStart

    totalDelay = model._totalDelay.X
    releaseTimes = _getModelReleaseTimes(model, epochInstance.trip_routes)
    congestedSchedule = _getModelSchedule(model, epochInstance.trip_routes)
    delaysOnArcs = _getModelDelayOnArcs(model, epochInstance.trip_routes)
    freeFlowSchedule = get_free_flow_schedule(epochInstance, congestedSchedule)
    staggeringApplied = _getStaggeringApplied(releaseTimes, epochStatusQuo.release_times)
    slack = get_staggering_applicable(epochInstance, staggeringApplied)
    totalTravelTime = get_total_travel_time(congestedSchedule)

    modelSolution = EpochSolution(delays_on_arcs=delaysOnArcs,
                                  free_flow_schedule=freeFlowSchedule,
                                  release_times=releaseTimes,
                                  staggering_applicable=slack,
                                  total_delay=totalDelay,
                                  congested_schedule=congestedSchedule,
                                  staggering_applied=staggeringApplied,
                                  vehicles_utilizing_arcs=epochStatusQuo.vehicles_utilizing_arcs,
                                  total_travel_time=totalTravelTime)

    return modelSolution
