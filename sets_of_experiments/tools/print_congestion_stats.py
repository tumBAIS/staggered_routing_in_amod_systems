import pandas as pd
import numpy as np
from tabulate import tabulate
import math


def print_arc_delays_distribution(results_df):
    """
    Process and print arc delay statistics for the given dataframe of experiments.

    Parameters:
        results_df (pd.DataFrame): Dataframe containing experiment results with relevant columns.
    """
    # Filter only the OFFLINE experiments (solver_parameters_epoch_size == 60)
    offline_df = results_df[results_df['solver_parameters_epoch_size'] == 60]

    # Split the dataframe into low and high flow constraint groups
    lc_df = offline_df[offline_df['instance_parameters_max_flow_allowed'] <= \
                       offline_df['instance_parameters_max_flow_allowed'].median()]
    hc_df = offline_df[offline_df['instance_parameters_max_flow_allowed'] > \
                       offline_df['instance_parameters_max_flow_allowed'].median()]

    # Helper function to calculate total delays statistics
    def calculate_arc_statistics(group_df):
        stats_dict = {}
        most_congested_stats_dict = {}

        for idx, (index, row) in enumerate(group_df.iterrows()):
            # Retrieve required columns
            arc_delays = row['status_quo_delays_on_arcs']  # list[list[float]]
            trip_routes = row['instance_trip_routes']  # list[list[int]]
            arc_mapping = row['arc_to_node_mapping']  # dict[int:tuple]
            travel_times = row['instance_travel_times_arcs']  # list[float]
            max_flow_allowed = row['instance_parameters_max_flow_allowed']

            # Flatten the list of delays and their corresponding arcs
            total_delays = []
            arc_delay_totals = {}
            for route_idx, route_delays in enumerate(arc_delays):
                for arc_idx, delay in enumerate(route_delays):
                    if delay > 0:  # Remove zero values
                        arc_id = trip_routes[route_idx][arc_idx]
                        arc_name = arc_mapping.get(arc_id, ("Unknown",))
                        total_delays.append(delay / 60)  # Convert seconds to minutes
                        if arc_name not in arc_delay_totals:
                            arc_delay_totals[arc_name] = []
                        arc_delay_totals[arc_name].append(delay / 60)

            # Calculate statistics for total delays only if delays exist
            if total_delays:
                most_congested_arc = max(arc_delay_totals, key=lambda x: sum(arc_delay_totals[x]))
                arc_delays = arc_delay_totals[most_congested_arc]
                stats_dict[idx] = {
                    'Sum': round(np.sum(total_delays), 2),
                    'Min': round(np.min(total_delays), 2),
                    'Max': round(np.max(total_delays), 2),
                    'Mean': round(np.mean(total_delays), 2),
                    'Median': round(np.median(total_delays), 2),
                    '10th Percentile': round(np.percentile(total_delays, 10), 2),
                    '90th Percentile': round(np.percentile(total_delays, 90), 2),
                    'Count': len(total_delays),
                }

                nominal_travel_time = travel_times[list(arc_mapping.keys())[
                    list(arc_mapping.values()).index(most_congested_arc)]] / 60
                nominal_capacity = math.ceil(nominal_travel_time * 60 / max_flow_allowed)

                most_congested_stats_dict[idx] = {
                    'Sum': round(np.sum(arc_delays), 2),
                    'Min': round(np.min(arc_delays), 2),
                    'Max': round(np.max(arc_delays), 2),
                    'Mean': round(np.mean(arc_delays), 2),
                    'Median': round(np.median(arc_delays), 2),
                    '10th Percentile': round(np.percentile(arc_delays, 10), 2),
                    '90th Percentile': round(np.percentile(arc_delays, 90), 2),
                    'Count': len(arc_delays),
                    'Nominal Travel Time (min)': round(nominal_travel_time, 2),
                    'Nominal Capacity': nominal_capacity,
                }

                # Ensure max delay in first table matches the sum of delays on the most congested arc
                stats_dict[idx]['Max'] = most_congested_stats_dict[idx]['Sum']
            else:
                stats_dict[idx] = {
                    'Sum': 0, 'Min': 0, 'Max': 0, 'Mean': 0,
                    'Median': 0, '10th Percentile': 0,
                    '90th Percentile': 0, 'Count': 0
                }
                most_congested_stats_dict[idx] = {
                    'Sum': 0, 'Min': 0, 'Max': 0, 'Mean': 0,
                    'Median': 0, '10th Percentile': 0,
                    '90th Percentile': 0, 'Count': 0,
                    'Nominal Travel Time (min)': 0, 'Nominal Capacity': 0
                }

        return stats_dict, most_congested_stats_dict

    # Helper function to print tables
    def print_table(data, title):
        df = pd.DataFrame(data)
        df.columns = [f'Instance {i + 1}' for i in range(df.shape[1])]
        print(f"\n--- {title} ---\n")
        print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=True))

    # Process Low Congestion group
    lc_stats, lc_most_congested = calculate_arc_statistics(lc_df)
    print_table(lc_stats, "Low Congestion Instances Total Delays (in minutes)")
    print_table(lc_most_congested, "Low Congestion Instances Most Congested Arc Delays (in minutes)")

    # Process High Congestion group
    hc_stats, hc_most_congested = calculate_arc_statistics(hc_df)
    print_table(hc_stats, "High Congestion Instances Total Delays (in minutes)")
    print_table(hc_most_congested, "High Congestion Instances Most Congested Arc Delays (in minutes)")
