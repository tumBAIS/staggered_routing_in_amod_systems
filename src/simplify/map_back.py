from problem.epoch_instance import EpochInstance
from problem.solution import Solution
import cpp_module as cpp
from input_data import SolverParameters


def map_simplified_epoch_solution(
        simplified_epoch_solution: Solution,
        cpp_epoch_instance: cpp.cpp_instance,
        solver_parameters: SolverParameters,
) -> Solution:
    """
    Maps the simplified epoch solution back to the full instance, including removed vehicles.
    """

    if not solver_parameters.simplify:
        return simplified_epoch_solution
    print("=" * 50)
    print(f"Mapping model solution -- Initial Delay: {simplified_epoch_solution.total_delay}.".center(50))
    print("=" * 50)

    # Compute the full congested schedule
    cpp_scheduler = cpp.cpp_scheduler(cpp_epoch_instance)
    cpp_solution = cpp_scheduler.construct_solution(simplified_epoch_solution.start_times)

    print("Full congested schedule computed.")

    print("=" * 50)
    print(f"Mapping completed successfully -- Final Delay: {cpp_solution.get_total_delay()}.".center(50))
    print("=" * 50)

    # Create and return the mapped epoch solution
    return Solution(
        total_delay=cpp_solution.get_total_delay(),
        congested_schedule=cpp_solution.get_schedule(),
        delays_on_arcs=cpp_solution.get_delays_on_arcs(cpp_epoch_instance),
        start_times=cpp_solution.get_start_times(),
        free_flow_schedule=cpp_epoch_instance.get_free_flow_schedule(cpp_solution.get_start_times()),
        total_travel_time=cpp_solution.get_total_travel_time(),
    )
