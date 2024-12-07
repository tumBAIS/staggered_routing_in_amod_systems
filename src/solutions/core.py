from input_data import SolverParameters
from MIP.model import construct_model, run_model
from solutions.status_quo import compute_solution_metrics, print_info_status_quo_metrics
from conflicting_sets.schedule_utilities import add_conflicting_sets_to_instance
from congestion_model.core import get_total_travel_time
from instance_module.instance import Instance
from solutions.map_simplified_epoch_solution import map_simplified_epoch_solution
from solutions.epoch_warm_start import get_epoch_warm_start
from solutions.model_solution import get_epoch_model_solution
from utils.classes import EpochSolution, CompleteSolution


def _print_header_offline_solution():
    print("#" * 20)
    print(f"COMPUTING OFFLINE SOLUTION")
    print("#" * 20)


def get_offline_solution(instance: Instance, releaseTimes: list[float],
                         solver_params: SolverParameters) -> CompleteSolution:
    """ Compute the global status quo to compare solution against """
    _print_header_offline_solution()
    solutionMetrics = compute_solution_metrics(instance, releaseTimes, solver_params)
    print_info_status_quo_metrics(solutionMetrics)
    add_conflicting_sets_to_instance(instance, solutionMetrics.free_flow_schedule)
    staggeringAppliedInEpoch = [0.0] * len(solutionMetrics.congested_schedule)
 
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


def _print_info_epoch_solution(epochStatusQuo, epochSolution):
    print("#" * 20)
    print(f"INFO EPOCH SOLUTION")
    print("#" * 20)

    print(f"Total delay epoch status quo: {epochStatusQuo.total_delay / 60 :.2f} [min]")
    print(f"Total delay epoch model solution: {epochSolution.total_delay / 60 :.2f} [min]")
    delayReduction = (epochStatusQuo.total_delay - epochSolution.total_delay) / epochStatusQuo.total_delay \
        if epochStatusQuo.total_delay > 1e-6 else 0
    print(f"Total delay epoch reduction: {delayReduction:.2%}")


def get_epoch_solution(simplifiedInstance, simplifiedStatusQuo, epochInstance, epochStatusQuo,
                       solver_params: SolverParameters) -> EpochSolution:
    if len(simplifiedStatusQuo.congested_schedule):
        epochWarmStart = get_epoch_warm_start(simplifiedInstance, simplifiedStatusQuo, solver_params)
        model = construct_model(simplifiedInstance, simplifiedStatusQuo, epochWarmStart, solver_params)
        run_model(model, simplifiedInstance, epochWarmStart, simplifiedStatusQuo, solver_params)
        modelSolution = get_epoch_model_solution(model, simplifiedInstance, simplifiedStatusQuo, epochWarmStart,
                                                 solver_params)
        # map back to the full system
        epochSolution = map_simplified_epoch_solution(epochInstance, modelSolution, solver_params)
        _print_info_epoch_solution(epochStatusQuo, epochSolution)
        return epochSolution
    else:
        return epochStatusQuo
