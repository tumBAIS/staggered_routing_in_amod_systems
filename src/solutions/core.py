from MIP.model import constructModel, runModel
from solutions.status_quo import computeSolutionMetrics, printInfoStatusQuoMetrics
from conflicting_sets.get import add_conflicting_sets_to_instance
from congestion_model.core import get_total_travel_time
from instanceModule.instance import Instance
from congestion_model.conflict_binaries import get_conflict_binaries
from solutions.map_simplified_epoch_solution import mapSimplifiedEpochSolution
from solutions.epoch_warm_start import getEpochWarmStart
from solutions.model_solution import getEpochModelSolution
from utils.classes import EpochSolution, CompleteSolution


def _printHeaderOfflineSolution():
    print("#" * 20)
    print(f"COMPUTING OFFLINE SOLUTION")
    print("#" * 20)


def get_offline_solution(instance: Instance, releaseTimes: list[float]) -> CompleteSolution:
    """ Compute the global status quo to compare solution against """
    _printHeaderOfflineSolution()
    solutionMetrics = computeSolutionMetrics(instance, releaseTimes)
    printInfoStatusQuoMetrics(solutionMetrics)
    add_conflicting_sets_to_instance(instance, solutionMetrics.freeFlowSchedule)
    staggeringAppliedInEpoch = [0.0] * len(solutionMetrics.congestedSchedule)
    # binaries = getConflictBinaries(instance.conflictingSets, instance.arcBasedShortestPaths,
    #                                solutionMetrics.congestedSchedule)  # for testing
    return CompleteSolution(
        delaysOnArcs=solutionMetrics.delaysOnArcs,
        freeFlowSchedule=solutionMetrics.freeFlowSchedule,
        releaseTimes=solutionMetrics.releaseTimes,
        staggeringApplicable=instance.maxStaggeringApplicable[:],
        totalDelay=solutionMetrics.totalDelay,
        congestedSchedule=solutionMetrics.congestedSchedule,
        staggeringApplied=staggeringAppliedInEpoch,
        totalTravelTime=get_total_travel_time(solutionMetrics.congestedSchedule),
        binaries=None
    )


def _printInfoEpochSolution(epochStatusQuo, epochSolution):
    print("#" * 20)
    print(f"INFO EPOCH SOLUTION")
    print("#" * 20)

    print(f"Total delay epoch status quo: {epochStatusQuo.totalDelay / 60 :.2f} [min]")
    print(f"Total delay epoch model solution: {epochSolution.totalDelay / 60 :.2f} [min]")
    delayReduction = (epochStatusQuo.totalDelay - epochSolution.totalDelay) / epochStatusQuo.totalDelay \
        if epochStatusQuo.totalDelay > 1e-6 else 0
    print(f"Total delay epoch reduction: {delayReduction:.2%}")


def get_epoch_solution(simplifiedInstance, simplifiedStatusQuo, epochInstance, epochStatusQuo) -> EpochSolution:
    if len(simplifiedStatusQuo.congestedSchedule):
        epochWarmStart = getEpochWarmStart(simplifiedInstance, simplifiedStatusQuo)
        model = constructModel(simplifiedInstance, simplifiedStatusQuo, epochWarmStart)
        runModel(model, simplifiedInstance, epochWarmStart, simplifiedStatusQuo)
        modelSolution = getEpochModelSolution(model, simplifiedInstance, simplifiedStatusQuo, epochWarmStart)
        # map back to the full system
        epochSolution = mapSimplifiedEpochSolution(epochInstance, modelSolution)
        _printInfoEpochSolution(epochStatusQuo, epochSolution)
        return epochSolution
    else:
        return epochStatusQuo
