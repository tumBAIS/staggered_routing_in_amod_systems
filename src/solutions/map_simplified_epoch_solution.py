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
    # Extract initial release times and removed vehicles for mapping
    release_times_epoch = epoch_instance.release_times
    removed_vehicles = epoch_instance.removed_vehicles

    # Reinsert removed vehicles into the schedule
    staggering_applied = simplified_epoch_solution.staggering_applied[:]
    staggering_applicable = simplified_epoch_solution.staggering_applicable[:]
    for vehicle in sorted(removed_vehicles):
        staggering_applied.insert(vehicle, 0)
        staggering_applicable.insert(vehicle, 0)

    # Calculate staggered release times for all vehicles
    staggered_release_times = [
        release_time + staggering
        for release_time, staggering in zip(release_times_epoch, staggering_applied)
    ]

    # Compute the full congested schedule
    congested_schedule = get_congested_schedule(epoch_instance, staggered_release_times, solver_params)

    # Compute additional metrics
    free_flow_schedule = get_free_flow_schedule(epoch_instance, congested_schedule)
    total_delay = get_total_delay(free_flow_schedule, congested_schedule)
    total_travel_time = get_total_travel_time(congested_schedule)
    delays_on_arcs = get_delays_on_arcs(epoch_instance, congested_schedule)

    # Update epoch timing and print summary
    epoch_instance.clock_end_epoch = datetime.datetime.now().timestamp()
    print(f"Time to complete the epoch: {epoch_instance.clock_end_epoch - epoch_instance.clock_start_epoch:.2f} [s]")
    print(f"Total delay mapped solution: {total_delay / 60:.2f} [min]")

    # Create and return the mapped epoch solution
    return Solution(
        total_delay=total_delay,
        congested_schedule=congested_schedule,
        delays_on_arcs=delays_on_arcs,
        release_times=staggered_release_times,
        staggering_applicable=staggering_applicable,
        free_flow_schedule=free_flow_schedule,
        staggering_applied=staggering_applied,
        total_travel_time=total_travel_time,
        vehicles_utilizing_arcs=simplified_epoch_solution.vehicles_utilizing_arcs,
    )
