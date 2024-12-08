import datetime

from input_data import SolverParameters
from utils.aliases import VehicleSchedules
from instance_module.epoch_instance import EpochInstance
from utils.classes import EpochSolution
from congestion_model.core import get_free_flow_schedule, \
    get_total_travel_time, get_delays_on_arcs, get_staggering_applicable
from congestion_model.conflict_binaries import get_conflict_binaries
import cpp_module as cpp


def _run_local_search(solution: EpochSolution, instance: EpochInstance, solver_params) -> VehicleSchedules:
    print("Computing warm start solution")
    instance.due_dates = instance.deadlines[:]
    totalTimeRemaining = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - instance.start_solution_time)
    epochTimeRemaining = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - instance.clock_start_epoch)
    timeRemaining = min(totalTimeRemaining, epochTimeRemaining)
    startSearchClock = datetime.datetime.now().timestamp()
    cppParameters = [
        timeRemaining,
    ]
    congestedSchedule = cpp.cppSchedulingLocalSearch(
        release_times=solution.release_times,
        remaining_time_slack=solution.staggering_applicable,
        staggering_applied=solution.staggering_applied,
        conflicting_sets=instance.conflicting_sets,
        earliest_departure_times=instance.earliest_departure_times,
        latest_departure_times=instance.latest_departure_times,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        trip_routes=instance.trip_routes,
        deadlines=instance.deadlines,
        due_dates=instance.due_dates,
        list_of_slopes=instance.input_data.list_of_slopes,
        list_of_thresholds=instance.input_data.list_of_thresholds,
        parameters=cppParameters,
        lb_travel_time=instance.get_lb_travel_time()
    )
    endSearchClock = datetime.datetime.now().timestamp()
    print("Time necessary to compute warm start solution: ", endSearchClock - startSearchClock)
    return congestedSchedule


def _check_if_there_time_left_for_optimization(epochInstance: EpochInstance, solver_params: SolverParameters):
    algorithmRuntime = solver_params.algorithm_time_limit - (
            datetime.datetime.now().timestamp() - epochInstance.start_solution_time)

    epochRuntime = solver_params.epoch_time_limit - (
            datetime.datetime.now().timestamp() - epochInstance.clock_start_epoch)

    timeLeft = min(algorithmRuntime, epochRuntime)
    return timeLeft > 1e-6


def get_epoch_warm_start(epochInstance: EpochInstance, epochStatusQuo: EpochSolution,
                         solver_params: SolverParameters) -> EpochSolution:
    isThereTimeLeftForOptimization = _check_if_there_time_left_for_optimization(epochInstance, solver_params)
    if solver_params.improve_warm_start and isThereTimeLeftForOptimization:
        congestedSchedule = _run_local_search(epochStatusQuo, epochInstance, solver_params)
    else:
        if not isThereTimeLeftForOptimization:
            print("no remaining time for optimization - ", end="")
        print("not improving status quo")
        return epochStatusQuo

    releaseTimes = [schedule[0] for schedule in congestedSchedule]
    freeFlowSchedule = get_free_flow_schedule(epochInstance, congestedSchedule)
    staggeringApplied = [congestedSchedule[vehicle][0] - releaseTime for vehicle, releaseTime in
                         enumerate(epochStatusQuo.release_times)]
    staggeringApplicable = get_staggering_applicable(epochInstance, staggeringApplied)
    delaysOnArcs = get_delays_on_arcs(epochInstance, congestedSchedule)
    totalDelay = sum(sum(delays) for delays in delaysOnArcs)
    binaries = get_conflict_binaries(epochInstance.conflicting_sets, epochInstance.trip_routes,
                                     congestedSchedule)
    totalTravelTime = get_total_travel_time(congestedSchedule)

    warmStart: EpochSolution = EpochSolution(total_delay=totalDelay,
                                             congested_schedule=congestedSchedule,
                                             delays_on_arcs=delaysOnArcs,
                                             release_times=releaseTimes,
                                             staggering_applicable=staggeringApplicable,
                                             binaries=binaries,
                                             free_flow_schedule=freeFlowSchedule,
                                             staggering_applied=staggeringApplied,
                                             total_travel_time=totalTravelTime,
                                             vehicles_utilizing_arcs=epochStatusQuo.vehicles_utilizing_arcs
                                             )
    print(f"The delay of the warm start is {totalDelay / totalTravelTime:.2%} of the travel time")
    return warmStart
