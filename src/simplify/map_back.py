from input_data import SolverParameters
from problem.epoch_instance import EpochInstance
from problem.solution import Solution
import cpp_module as cpp


def map_simplified_epoch_solution(
        epoch_instance: EpochInstance,
        simplified_epoch_solution: Solution,
        cpp_epoch_instance: cpp.cpp_instance
) -> Solution:
    """
    Maps the simplified epoch solution back to the full instance, including removed vehicles.
    """
    print("\n" + "=" * 50)
    print(
        f"Mapping Simplified Solution to Full Instance -- Initial Delay: {simplified_epoch_solution.total_delay}".center(
            50))
    print("=" * 50)

    # Extract initial release times and removed vehicles for mapping
    release_times_epoch = epoch_instance.release_times
    removed_vehicles = epoch_instance.removed_vehicles
    min_release_time = min(release_times_epoch)
    # Reinsert removed vehicles into the schedule
    staggered_release_times = [x + min_release_time for x in simplified_epoch_solution.start_times]
    for trip_id in sorted(removed_vehicles):
        staggered_release_times.insert(trip_id, release_times_epoch[trip_id])

    print(f"Reinserted {len(removed_vehicles)} removed vehicles.")

    # Compute the full congested schedule
    cpp_scheduler = cpp.cpp_scheduler(cpp_epoch_instance)
    cpp_solution = cpp_scheduler.construct_solution(staggered_release_times)

    print("Full congested schedule computed.")

    # Compute additional metrics
    epoch_instance.set_clock_end_epoch()

    print("=" * 50)
    print(f"Mapping completed successfully -- Final Delay: {cpp_solution.get_total_delay()}.".center(50))
    print("=" * 50)

    # Create and return the mapped epoch solution
    return Solution(
        total_delay=cpp_solution.get_total_delay(),
        congested_schedule=cpp_solution.get_schedule(),
        delays_on_arcs=cpp_solution.get_delays_on_arcs(),
        start_times=staggered_release_times,
        free_flow_schedule=cpp_epoch_instance.get_free_flow_schedule(cpp_solution.get_start_times()),
        total_travel_time=cpp_solution.get_total_travel_time(),
    )
