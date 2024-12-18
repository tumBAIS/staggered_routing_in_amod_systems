import datetime
from input_data import SolverParameters
from congestion_model.core import (
    get_congested_schedule,
    get_free_flow_schedule,
    get_total_travel_time,
    get_total_delay,
    get_delays_on_arcs,
)
from instance_module.epoch_instance import EpochInstance
from utils.classes import Solution


def map_simplified_epoch_solution(
        epoch_instance: EpochInstance,
        simplified_epoch_solution: Solution,
        solver_params: SolverParameters,
) -> Solution:
    """
    Maps the simplified epoch solution back to the full instance, including removed vehicles.

    This function reinserts removed vehicles into the schedule, adjusts release times,
    computes the updated schedules and delays, and returns the full epoch solution.
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
    staggered_release_times = [x + min_release_time for x in simplified_epoch_solution.release_times]
    for trip_id in sorted(removed_vehicles):
        staggered_release_times.insert(trip_id, release_times_epoch[trip_id])

    print(f"Reinserted {len(removed_vehicles)} removed vehicles.")

    # Compute the full congested schedule
    congested_schedule = get_congested_schedule(epoch_instance, staggered_release_times, solver_params)
    print("Full congested schedule computed.")

    # Compute additional metrics
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    total_delay = get_total_delay(free_flow_schedule, congested_schedule)
    total_travel_time = get_total_travel_time(congested_schedule)
    delays_on_arcs = get_delays_on_arcs(epoch_instance, congested_schedule)

    # Update epoch timing and print summary
    epoch_instance.clock_end_epoch = datetime.datetime.now().timestamp()

    print("=" * 50)
    print(f"Mapping completed successfully -- Final Delay: {total_delay}.".center(50))
    print("=" * 50)

    # Create and return the mapped epoch solution
    return Solution(
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        release_times=staggered_release_times,
        free_flow_schedule=free_flow_schedule,
        total_travel_time=total_travel_time,
        vehicles_utilizing_arcs=simplified_epoch_solution.vehicles_utilizing_arcs,
    )
