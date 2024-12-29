import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import os
import tikzplotlib
from collections import defaultdict
import numpy as np


# Compute conflicting_sets_before_processing
def compute_conflicting_sets(trip_routes, capacities):
    conflicting_sets = defaultdict(list)
    for trip_id, arcs in enumerate(trip_routes):
        for arc in arcs:
            if arc != 0:  # Ignore the dummy arc (0)
                conflicting_sets[arc].append(trip_id)
    # Remove conflicting sets that fit within capacity
    for arc, trips in conflicting_sets.items():
        try:
            if len(trips) <= capacities[arc]:
                conflicting_sets[arc] = []

        except:
            raise RuntimeError
    return [trips for trips in conflicting_sets.values() if trips]  # Filter out empty lists


def get_barplot_conflicting_sets(results_df: pd.DataFrame, path_to_figures: Path, verbose: bool = False):
    print("=" * 50)
    print("Step 1: Filtering DataFrame for offline experiments".center(50))
    print("=" * 50)

    # Filter the DataFrame for offline experiments
    offline_df = results_df[results_df['solver_parameters_epoch_size'] == 60]

    print("=" * 50)
    print("Step 2: Computing conflicting sets before processing".center(50))
    print("=" * 50)

    # Compute capacities
    offline_df['capacities'] = offline_df.apply(
        lambda row: [int(np.ceil(time / row['instance_parameters_max_flow_allowed'])) for time in
                     row['instance_travel_times_arcs']],
        axis=1
    )

    offline_df['conflicting_sets_before_processing'] = offline_df.apply(
        lambda row: compute_conflicting_sets(row['instance_trip_routes'], row['capacities']), axis=1
    )

    print("=" * 50)
    print("Step 3: Dividing DataFrame into LC and HC subsets".center(50))
    print("=" * 50)

    # Divide the DataFrame into LC and HC subsets
    lc_df = offline_df[offline_df['congestion_level'] == 'LC']
    hc_df = offline_df[offline_df['congestion_level'] == 'HC']

    def get_max_y(df, columns):
        max_y = 0
        for column in columns:
            all_sets = [len(conflict_set) for instance in df[column] for conflict_set in instance if
                        len(conflict_set) > 0]
            bin_counts, _ = np.histogram(all_sets, bins=range(0, max(all_sets, default=0) + 5, 5))
            max_y = max(max_y, max(bin_counts, default=0))
        return max_y + 1000  # Add slack of 10

    # Determine the maximum y-axis height for LC and HC
    lc_max_y = get_max_y(lc_df, ['conflicting_sets_before_processing', 'instance_conflicting_sets'])
    hc_max_y = get_max_y(hc_df, ['conflicting_sets_before_processing', 'instance_conflicting_sets'])

    def plot_conflicting_sets(df, column, title, file_name, max_y):
        print("=" * 50)
        print(f"Step 4: Plotting {title}".center(50))
        print("=" * 50)

        # Flatten the list of conflicting sets and calculate their sizes
        all_sets = [len(conflict_set) for instance in df[column] for conflict_set in instance if len(conflict_set) > 0]

        # Create bins of size 5
        bins = range(0, max(all_sets, default=0) + 2, 2)

        # Compute statistics for bins if verbose is enabled
        if verbose:
            print(f"\nStatistics for {title}:")
            bin_counts, bin_edges = np.histogram(all_sets, bins=bins)
            for i in range(len(bin_counts)):
                bin_min = bin_edges[i]
                bin_max = bin_edges[i + 1]
                count = bin_counts[i]
                points_in_bin = [x for x in all_sets if bin_min <= x < bin_max]
                min_point = min(points_in_bin) if points_in_bin else None
                max_point = max(points_in_bin) if points_in_bin else None
                print(f"  Bin {i + 1}: [{bin_min}, {bin_max}) - Count: {count}, Min: {min_point}, Max: {max_point}")

        # Plot the frequency barplot
        plt.figure(figsize=(6.5, 4.0))
        plt.hist(all_sets, bins=bins, edgecolor="black", alpha=0.7)

        plt.title(title)
        plt.xlabel("Conflicting Set Size")
        plt.ylabel("Frequency")
        plt.ylim(1, 5e5)
        plt.yscale("log")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save the figure as JPEG and TeX
        os.makedirs(path_to_figures / "conflicting_sets", exist_ok=True)
        plt.savefig(path_to_figures / "conflicting_sets" / f"{file_name}.jpeg", format="jpeg", dpi=300)

        tikzplotlib.save(
            str(path_to_figures / "conflicting_sets" / f"{file_name}.tex"),
            axis_width="\DelayReductionWidth",
            axis_height="\DelayReductionHeight"
        )
        plt.close()

        print(f"Finished plotting {title}")

    # Generate barplots for conflicting sets before and after processing
    plot_conflicting_sets(lc_df, 'conflicting_sets_before_processing',
                          "LC Scenario: Conflicting Sets Before Processing",
                          "lc_conflicting_sets_before", lc_max_y)
    plot_conflicting_sets(lc_df, 'instance_conflicting_sets',
                          "LC Scenario: Conflicting Sets After Processing",
                          "lc_conflicting_sets_after", lc_max_y)

    plot_conflicting_sets(hc_df, 'conflicting_sets_before_processing',
                          "HC Scenario: Conflicting Sets Before Processing",
                          "hc_conflicting_sets_before", hc_max_y)
    plot_conflicting_sets(hc_df, 'instance_conflicting_sets',
                          "HC Scenario: Conflicting Sets After Processing",
                          "hc_conflicting_sets_after", hc_max_y)

    print("=" * 50)
    print("All operations completed successfully".center(50))
    print("=" * 50)
