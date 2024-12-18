import datetime
import pandas as pd

from input_data import TOLERANCE
from problem.epoch_instance import EpochInstances
from problem.instance import Instance
from problem.solution import Solution


def print_conflicting_sets_info(instance: Instance):
    """
    Prints information about the sizes of conflicting sets and related statistics.

    Args:
        instance: The problem instance containing conflicting sets data.
    """
    print("=" * 50)
    print(f"Conflicting Sets Information".center(50))
    print("=" * 50)

    # Check if there are any conflicting sets
    conflicting_sets_sizes = [len(x) for x in instance.conflicting_sets if x]
    if not conflicting_sets_sizes:
        print("No conflicting sets found.")
        print("=" * 50)
        return

    # Convert conflicting sets sizes into a Pandas Series for statistical analysis
    conf_set_series = pd.Series(conflicting_sets_sizes)

    # Transpose and print summary statistics
    print("Summary Statistics:")
    print(conf_set_series.describe().to_frame(name="Value").T.round(2))

    # Identify the arc with the largest conflicting set
    arc_with_largest_set = max(
        range(len(instance.travel_times_arcs)),
        key=lambda x: len(instance.conflicting_sets[x])
    )
    largest_set_size = len(instance.conflicting_sets[arc_with_largest_set])

    # Print details about the largest conflicting set
    print("\nDetails of the Largest Conflicting Set:")
    print(f"- Arc ID: {arc_with_largest_set}")
    print(f"- Conflicting Set Size: {largest_set_size}")
    print(f"- Free Flow Travel Time: {instance.travel_times_arcs[arc_with_largest_set] / 60:.2f} [min]")
    print(f"- Nominal Capacity: {instance.capacities_arcs[arc_with_largest_set]}")

    # Calculate outliers (Above Q3 + 1.5*IQR)
    Q1, Q3 = conf_set_series.quantile([0.25, 0.75])
    IQR = Q3 - Q1
    outliers = conf_set_series[conf_set_series >= Q3 + 1.5 * IQR]

    print("\nOutliers (Above 75th Percentile + 1.5 * IQR):")
    if not outliers.empty:
        print(outliers.describe().to_frame(name="Value").T.round(2))
    else:
        print("No outliers found.")

    print("=" * 50)


def _calculate_trip_lengths_in_minutes(schedule):
    return [(schedule[vehicle][-1] - schedule[vehicle][0]) / 60 for vehicle in range(len(schedule))]


def _calculate_time_differences(length_congested, length_free_flow):
    return [length_congested[i] - length_free_flow[i] for i in range(len(length_free_flow))]


def _create_length_trips_dataframe(congested_schedule, free_flow_schedule):
    length_congested = _calculate_trip_lengths_in_minutes(congested_schedule)
    length_free_flow = _calculate_trip_lengths_in_minutes(free_flow_schedule)
    time_difference = _calculate_time_differences(length_congested, length_free_flow)

    return pd.DataFrame({
        "Congested Trip Time [min]": length_congested,
        "Free Flow Trip Time [min]": length_free_flow,
        "Time Difference [min]": time_difference,
    })


def _get_delays_on_arcs_in_minutes_series(instance, delays_on_arcs):
    data = {
        'Nominal Travel Time [min]': [],
        'Delay on Arcs [min]': [],
    }

    for vehicle, delays in enumerate(delays_on_arcs):
        for position, delay in enumerate(delays):
            if delay > TOLERANCE:
                arc = instance.trip_routes[vehicle][position]
                travel_time = instance.travel_times_arcs[arc] / 60  # Convert to minutes
                delay_min = delay / 60  # Convert to minutes

                data['Nominal Travel Time [min]'].append(travel_time)
                data['Delay on Arcs [min]'].append(delay_min)

    return pd.DataFrame(data)


def print_trips_info(instance, congested_schedule, free_flow_schedule, delays_on_arcs):
    """
    Prints combined information about trip lengths and delays on arcs side-by-side.

    Args:
        instance: The problem instance containing trip and arc data.
        congested_schedule: The congested trip schedule.
        free_flow_schedule: The free-flow trip schedule.
        delays_on_arcs: Delay data for arcs.
    """
    print("=" * 100)
    print("Offline Solution - Trips Info".center(100))
    print("=" * 100)

    # Trip Length Info
    length_trips_df = _create_length_trips_dataframe(congested_schedule, free_flow_schedule)
    length_congested_trips_df = length_trips_df[length_trips_df['Time Difference [min]'] > TOLERANCE]
    trip_length_summary = length_trips_df.describe().round(2).T
    congested_trip_length_summary = length_congested_trips_df.describe().round(2).T

    # Delays on Arcs Info
    delays_on_arcs_series = _get_delays_on_arcs_in_minutes_series(instance, delays_on_arcs)
    delay_summary = delays_on_arcs_series.describe().round(2).T

    # Combine outputs into one transposed format
    combined_table = pd.concat(
        [trip_length_summary, congested_trip_length_summary, delay_summary],
        axis=0,
        keys=["All Trips", "Congested Trips", "Delays on Arcs"]
    )

    # Print summaries
    with pd.option_context('display.max_columns', None, 'display.width', 1000):
        print(combined_table)
        print("=" * 100)


def print_unified_solution_construction_start() -> None:
    """
    Prints a message to indicate that computations across epochs are complete
    and the unified solution is being constructed.
    """
    print("\n" + "=" * 50)
    print("Computation Across Epochs Complete".center(50))
    print("=" * 50)
    print("Now constructing the unified solution...".center(50))
    print("=" * 50)


def print_insights_algorithm(complete_status_quo: Solution, reconstructed_solution: Solution,
                             epoch_instances: EpochInstances):
    print("=" * 50)
    print("Final Algorithm Insights".center(50))
    print("=" * 50)

    delay_reduction = (complete_status_quo.total_delay - reconstructed_solution.total_delay) / \
                      complete_status_quo.total_delay if complete_status_quo.total_delay > TOLERANCE else 0

    print(f"- Total Delay - Complete Status Quo: {complete_status_quo.total_delay / 60:.2f} [min]")
    print(f"- Total Delay - Final Solution: {reconstructed_solution.total_delay / 60:.2f} [min]")
    print(f"- Total Delay Reduction: {delay_reduction:.2%}")
    print(f"- Total Runtime: {datetime.datetime.now().timestamp() - epoch_instances[0].clock_start_epoch:.2f} [s]")
    print("=" * 50)
