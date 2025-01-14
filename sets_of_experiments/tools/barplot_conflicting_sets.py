import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import os
import tikzplotlib
from collections import defaultdict
import numpy as np
from matplotlib.ticker import AutoMinorLocator, LogLocator


# Function to generate the minor ytick string
def generate_minor_yticks(ymin, ymax, base=10, subs=np.arange(1, 10)):
    """
    Generate a string for minor y-ticks in a logarithmic scale.

    :param ymin: Minimum value of y-axis.
    :param ymax: Maximum value of y-axis.
    :param base: Base of the logarithmic scale (default is 10).
    :param subs: Subdivisions within each decade (default is 1-9).
    :return: String for minor y-ticks.
    """
    ticks = []
    exp_min = int(np.floor(np.log10(ymin)))
    exp_max = int(np.ceil(np.log10(ymax)))
    for exponent in range(exp_min, exp_max):
        ticks.extend([base ** exponent * sub for sub in subs])
    # Filter ticks within the range
    ticks = [tick for tick in ticks if ymin <= tick <= ymax]
    return f"minor ytick={{{','.join(map(str, ticks))}}}"


# Compute conflicting_sets_before_processing
def compute_conflicting_sets(trip_routes, capacities):
    conflicting_sets = defaultdict(list)
    for trip_id, arcs in enumerate(trip_routes):
        for arc in arcs:
            if arc != 0:  # Ignore the dummy arc (0)
                conflicting_sets[arc].append(trip_id)
    # Remove conflicting sets that fit within capacity
    for arc, trips in conflicting_sets.items():
        if len(trips) <= capacities[arc]:
            conflicting_sets[arc] = []
    return [trips for trips in conflicting_sets.values() if trips]  # Filter out empty lists


def get_barplot_conflicting_sets(results_df: pd.DataFrame, path_to_figures: Path, verbose: bool = False):
    print("=" * 50)
    print("Step 1: Filtering DataFrame for offline experiments".center(50))
    print("=" * 50)

    # Filter the DataFrame for offline experiments
    offline_df = results_df[results_df['solver_parameters_epoch_size'] == 60].copy()

    print("=" * 50)
    print("Step 2: Computing conflicting sets before processing".center(50))
    print("=" * 50)

    # Compute capacities
    offline_df.loc[:, 'capacities'] = offline_df.apply(
        lambda row: [int(np.ceil(time / row['instance_parameters_max_flow_allowed'])) for time in
                     row['instance_travel_times_arcs']],
        axis=1
    )

    # Compute conflicting sets before processing
    offline_df.loc[:, 'conflicting_sets_before_processing'] = offline_df.apply(
        lambda row: compute_conflicting_sets(row['instance_trip_routes'], row['capacities']),
        axis=1
    )

    print("=" * 50)
    print("Step 3: Dividing DataFrame into LC and HC subsets".center(50))
    print("=" * 50)

    # Divide the DataFrame into LC and HC subsets
    lc_df = offline_df[offline_df['congestion_level'] == 'LC']
    hc_df = offline_df[offline_df['congestion_level'] == 'HC']

    max_y = 5e5 + 1

    def plot_conflicting_sets(df, column, file_name, max_y, x_limit, bin_size=10, min_y=10):
        print("=" * 50)
        print(f"Step 4: Plotting {file_name}".center(50))
        print("=" * 50)

        # Flatten the list of conflicting sets and calculate their sizes
        all_sets = [len(conflict_set) for instance in df[column] for conflict_set in instance if len(conflict_set) > 0]

        # Create bins of size bin_size
        bins = range(0, x_limit + bin_size, bin_size)

        # Plot the frequency barplot
        plt.figure(figsize=(5 / 2.54, 5 / 2.54))  # Convert cm to inches
        plt.hist(all_sets, bins=bins, edgecolor="black", alpha=1, zorder=1, color="#0077b6")

        # Set labels
        plt.xlabel(r"\$\ConflictingSetSize{\Arc}\$")
        plt.ylabel("Observations")
        plt.ylim(min_y, max_y)
        plt.xlim(0, x_limit)
        plt.yscale("log")

        # Enable minor ticks on the y-axis
        ax = plt.gca()  # Get current axes
        ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(1.0, 10.0) * 0.1, numticks=10))  # For log scale
        ax.yaxis.set_minor_formatter(plt.NullFormatter())  # Optionally hide labels for minor ticks

        # Ensure the axes borders are on top of the histogram
        ax.spines['top'].set_zorder(2)
        ax.spines['right'].set_zorder(2)
        ax.spines['left'].set_zorder(2)
        ax.spines['bottom'].set_zorder(2)
        ax.tick_params(axis='both', which='both', zorder=2)

        # Place the grid behind the bars
        plt.grid(axis='y', which='major', linestyle='--', alpha=0.7, zorder=0)
        plt.grid(axis='y', which='minor', linestyle=':', alpha=0.5, zorder=0)  # Minor grid lines

        plt.tight_layout()

        # Save the figure as JPEG
        os.makedirs(path_to_figures / "conflicting_sets", exist_ok=True)
        plt.savefig(path_to_figures / "conflicting_sets" / f"{file_name}.jpeg", format="jpeg", dpi=300)

        # Save the figure as TeX
        tex_path = path_to_figures / "conflicting_sets" / f"{file_name}.tex"
        tikzplotlib.save(
            str(tex_path),
            axis_width="5cm",
            axis_height="5cm"
        )

        # Modify the TeX output
        with open(tex_path, 'r') as tex_file:
            tex_content = tex_file.readlines()

        with open(tex_path, 'w') as tex_file:
            for line in tex_content:
                # Comment out "log basis y={10},"
                if "log basis y={10}," in line:
                    tex_file.write(f"% {line}")  # Comment out the line
                elif "xlabel={\$\ConflictingSetSize{\Arc}\$}," in line:
                    tex_file.write(line.replace("\$\ConflictingSetSize{\Arc}\$",
                                                "$\ConflictingSetSize{\Arc}$"))
                elif "\\begin{axis}" in line:
                    tex_file.write(line)
                    tex_file.write(f"{generate_minor_yticks(min_y, max_y)},\n")
                else:
                    tex_file.write(line)  # Write unmodified lines

        plt.close()
        print(f"Finished plotting {file_name}")

    # Determine the maximum x-axis limit for all plots
    x_limit = max(
        max(len(conflict_set) for instance in offline_df['conflicting_sets_before_processing'] for conflict_set in
            instance if len(conflict_set) > 0),
        max(len(conflict_set) for instance in lc_df['instance_conflicting_sets'] for conflict_set in instance if
            len(conflict_set) > 0),
        max(len(conflict_set) for instance in hc_df['instance_conflicting_sets'] for conflict_set in instance if
            len(conflict_set) > 0)
    )

    # Generate barplots with adjusted settings
    plot_conflicting_sets(
        offline_df, 'conflicting_sets_before_processing',
        "before", max_y, x_limit
    )

    plot_conflicting_sets(
        lc_df, 'instance_conflicting_sets',
        "after_lc", max_y, x_limit
    )

    plot_conflicting_sets(
        hc_df, 'instance_conflicting_sets',
        "after_hc", max_y, x_limit
    )

    print("=" * 50)
    print("All operations completed successfully".center(50))
    print("=" * 50)
