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
    add_conflicting_sets_to_instance(instance, solutionMetrics.free_flow_schedule)
    staggeringAppliedInEpoch = [0.0] * len(solutionMetrics.congested_schedule)
    # binaries = getConflictBinaries(instance.conflictingSets, instance.arcBasedShortestPaths,
    #                                solutionMetrics.congestedSchedule)  # for testing
    return CompleteSolution(
        delays_on_arcs=solutionMetrics.delays_on_arcs,
        free_flow_schedule=solutionMetrics.free_flow_schedule,
        release_times=solutionMetrics.release_times,
        staggering_applicable=instance.max_staggering_applicable[:],
        total_delay=solutionMetrics.total_delay,
        congested_schedule=solutionMetrics.congested_schedule,
        staggering_applied=staggeringAppliedInEpoch,
        total_travel_time=get_total_travel_time(solutionMetrics.congested_schedule),
        binaries=None
    )


def _printInfoEpochSolution(epochStatusQuo, epochSolution):
    print("#" * 20)
    print(f"INFO EPOCH SOLUTION")
    print("#" * 20)

    print(f"Total delay epoch status quo: {epochStatusQuo.total_delay / 60 :.2f} [min]")
    print(f"Total delay epoch model solution: {epochSolution.total_delay / 60 :.2f} [min]")
    delayReduction = (epochStatusQuo.total_delay - epochSolution.total_delay) / epochStatusQuo.total_delay \
        if epochStatusQuo.total_delay > 1e-6 else 0
    print(f"Total delay epoch reduction: {delayReduction:.2%}")


def get_epoch_solution(simplifiedInstance, simplifiedStatusQuo, epochInstance, epochStatusQuo) -> EpochSolution:
    if len(simplifiedStatusQuo.congested_schedule):
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
