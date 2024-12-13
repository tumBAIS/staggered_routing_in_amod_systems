import datetime
import pandas as pd

from input_data import SPEED_KPH, TOLERANCE
from instance_module.epoch_instance import EpochInstances
from utils.classes import Solution


def print_info_arcs_utilized(instance):
    length_arcs = _calculate_length_arcs_utilized(instance)
    dataframe_info = _create_info_dataframe(instance, length_arcs)
    _print_arcs_utilized_info(dataframe_info)


def print_info_conflicting_sets_sizes(instance):
    """Prints information about sizes of conflicting sets and related statistics."""
    conflicting_sets_sizes = [len(x) for x in instance.conflicting_sets if x]
    conf_set_series = pd.Series(conflicting_sets_sizes)

    print("=" * 50)
    print("Distributional Info - Conflicting Sets".center(50))
    print("=" * 50)

    print(conf_set_series.describe())

    arc_with_largest_set = max(
        range(len(instance.travel_times_arcs)),
        key=lambda x: len(instance.conflicting_sets[x])
    )
    largest_set_size = len(instance.conflicting_sets[arc_with_largest_set])

    print(f"\nInfo - Arc with Largest Conflicting Set:")
    print(f"- Arc ID: {arc_with_largest_set}")
    print(f"- Conflicting Set Size: {largest_set_size}")
    print(f"- Free Flow Travel Time: {instance.travel_times_arcs[arc_with_largest_set]} [s]")
    print(f"- Nominal Capacity: {instance.capacities_arcs[arc_with_largest_set]}")

    Q1, Q3 = conf_set_series.quantile([0.25, 0.75])
    IQR = Q3 - Q1
    outliers = conf_set_series[conf_set_series >= Q3 + 1.5 * IQR]

    print("\nInfo - Outliers (Above 75th Percentile + 1.5 * IQR):")
    print(outliers.describe())
    print("=" * 50)


def print_info_length_trips(instance, congested_schedule, free_flow_schedule, delays_on_arcs):
    """Prints information about trip lengths, delays on arcs, and deadlines."""
    length_trips_df = _create_length_trips_dataframe(congested_schedule, free_flow_schedule)
    length_congested_trips_df = length_trips_df[length_trips_df['Time Difference [min]'] > TOLERANCE]

    pd.options.display.float_format = '{:.2f}'.format

    _print_length_all_trips_info(length_trips_df)
    _print_length_congested_trips_info(length_congested_trips_df)
    _print_delays_on_arcs_info(instance, delays_on_arcs)


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


def _print_length_all_trips_info(length_trips_df):
    print("=" * 50)
    print("Trip Length Info - All Trips [min]".center(50))
    print("=" * 50)
    print(length_trips_df.describe())
    print("=" * 50, "\n")


def _print_length_congested_trips_info(length_congested_trips_df):
    print("=" * 50)
    print("Trip Length Info - Congested Trips [min]".center(50))
    print("=" * 50)
    print(length_congested_trips_df.describe())
    print("=" * 50, "\n")


def _print_delays_on_arcs_info(instance, delays_on_arcs):
    delays_on_arcs_series = _get_delays_on_arcs_in_minutes_series(instance, delays_on_arcs)
    print("=" * 50)
    print("Delay Info - Arcs [min]".center(50))
    print("=" * 50)
    print(delays_on_arcs_series.describe())
    print("=" * 50, "\n")


def _calculate_length_arcs_utilized(instance):
    return [travel_time * SPEED_KPH / 3.6 for travel_time in instance.travel_times_arcs]


def _create_info_dataframe(instance, length_arcs):
    return pd.DataFrame({
        "Length [m]": length_arcs,
        "Travel Times [min]": [x / 60 for x in instance.travel_times_arcs],
        "Nominal Capacities": instance.capacities_arcs,
    })


def _print_arcs_utilized_info(dataframe_info):
    print("=" * 50)
    print("Info - Arcs Utilized".center(50))
    print("=" * 50)
    print(dataframe_info.describe().round(2))
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
