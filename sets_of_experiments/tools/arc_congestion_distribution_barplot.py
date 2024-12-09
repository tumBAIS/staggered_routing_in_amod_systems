import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import tikzplotlib


def get_arc_congestion_distribution_barplot(results_df: pd.DataFrame, path_to_figures: Path,
                                            verbose: bool = False) -> None:
    """
    Generate barplots for arc congestion distributions for UNC, OFF, and ON scenarios.
    """

    print("\n" + "=" * 50)
    print("Starting get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")

    # Step 1: Split DataFrame into offline and online data
    print("Step 1: Splitting the DataFrame...".center(50))
    offline_df = results_df[results_df["solver_parameters_epoch_size"] == 60]
    online_df = results_df[results_df["solver_parameters_epoch_size"] != 60]
    print(f"Offline DataFrame contains {len(offline_df)} rows.".center(50))
    print(f"Online DataFrame contains {len(online_df)} rows.".center(50))

    # Helper function to calculate total delays per arc
    def calculate_arc_delays(data, delay_column, arc_to_node_mapping):
        arc_delays = {}
        for _, row in data.iterrows():
            delays_on_arcs = row[delay_column]
            arc_mapping = row[arc_to_node_mapping]
            for trip, delays in zip(row["instance_trip_routes"], delays_on_arcs):
                for arc, delay in zip(trip, delays):
                    if arc != 0 and arc in arc_mapping:  # Ignore dummy arcs
                        node_pair = arc_mapping[arc]
                        if node_pair not in arc_delays:
                            arc_delays[node_pair] = 0
                        arc_delays[node_pair] += delay
        return arc_delays

    # Step 2: Calculate total delays for UNC, OFF, and ON
    print("\nStep 2: Calculating total delays for UNC, OFF, and ON...".center(50))
    unc_delays = calculate_arc_delays(offline_df, "status_quo_delays_on_arcs", "arc_to_node_mapping")
    off_delays = calculate_arc_delays(offline_df, "solution_delays_on_arcs", "arc_to_node_mapping")
    on_delays = calculate_arc_delays(online_df, "solution_delays_on_arcs", "arc_to_node_mapping")
    print("Total delays calculated.".center(50))

    # Filter out arcs with a maximum delay of at most 1e-2 in all barplots
    print("\nStep 3: Filtering arcs...".center(50))
    all_arcs = set(unc_delays.keys()) | set(off_delays.keys()) | set(on_delays.keys())
    filtered_arcs = {arc for arc in all_arcs if max(unc_delays.get(arc, 0), off_delays.get(arc, 0),
                                                    on_delays.get(arc, 0)) > 1e-2}

    unc_delays = {arc: delay for arc, delay in unc_delays.items() if arc in filtered_arcs}
    off_delays = {arc: delay for arc, delay in off_delays.items() if arc in filtered_arcs}
    on_delays = {arc: delay for arc, delay in on_delays.items() if arc in filtered_arcs}

    print(f"Filtered arcs to {len(filtered_arcs)} remaining.".center(50))

    # Step 4: Create frequency bins for delays
    print("\nStep 4: Creating frequency bins...".center(50))
    bins = [-1e-2, 1e-2] + list(
        np.arange(10, 310, 10))  # First bin: [-1e-2, 1e-2], subsequent bins: 10-second intervals
    unc_values = list(unc_delays.values())
    off_values = list(off_delays.values())
    on_values = list(on_delays.values())

    unc_freq, unc_bins = np.histogram(unc_values, bins=bins)
    off_freq, off_bins = np.histogram(off_values, bins=bins)
    on_freq, on_bins = np.histogram(on_values, bins=bins)

    # Print data falling into each bin
    def print_bin_data(bin_edges, freq, label, values):
        print(f"\n{label} Bin Data:")
        for i in range(len(bin_edges) - 1):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            bin_values = [v for v in values if lower <= v < upper]
            print(f"Bin {i}: [{lower}, {upper}] - Count: {freq[i]}, Values: {bin_values}")

    if verbose:
        print_bin_data(unc_bins, unc_freq, "UNC", unc_values)
        print_bin_data(off_bins, off_freq, "OFF", off_values)
        print_bin_data(on_bins, on_freq, "ON", on_values)

    # Combine frequencies to determine which bins have data
    combined_freq = unc_freq + off_freq + on_freq
    valid_bins = [i for i, freq in enumerate(combined_freq) if freq > 0]

    # Filter bins and frequencies
    filtered_bins = [bins[i] for i in valid_bins] + [bins[max(valid_bins) + 1]]
    unc_freq = unc_freq[valid_bins]
    off_freq = off_freq[valid_bins]
    on_freq = on_freq[valid_bins]

    # Step 5: Create barplots
    print("\nStep 5: Creating barplots...".center(50))
    bar_width = 0.3
    x = np.arange(len(filtered_bins) - 1)  # X positions for the bars

    plt.figure(figsize=(8, 5))
    plt.grid(axis="y", linestyle="--", color="gray", alpha=0.7, which="major", zorder=0)
    plt.grid(axis="y", linestyle="--", color="lightgray", alpha=0.4, which="minor", zorder=0)

    plt.bar(x - bar_width, unc_freq, width=bar_width, color="gray", edgecolor="black", label="UNC", hatch="/",
            zorder=2)
    plt.bar(x, off_freq, width=bar_width, color="white", edgecolor="black", label="OFF", hatch=".", zorder=2)
    plt.bar(x + bar_width, on_freq, width=bar_width, color="lightgray", edgecolor="black", label="ON", hatch="\\",
            zorder=2)

    # Step 6: Customize plot aesthetics
    plt.yscale("log")  # Use logarithmic scale for the y-axis
    plt.xlabel(r"$\mathcal{E}_a$ [min]")
    plt.ylabel("Observations")

    # Custom X-Ticks: First bin is "0", others are upper bounds (e.g., "10", "20", ...)
    xticks = [f"{int(filtered_bins[i])}" for i in range(1, len(filtered_bins))]
    plt.xticks(x, xticks, rotation=0)
    plt.legend(loc="upper right", title=None, frameon=True, framealpha=1, facecolor="white", edgecolor="black")
    plt.tight_layout()

    # Step 7: Save the plot
    output_dir = path_to_figures / "arc_congestion_distribution"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_dir / "arc_congestion_distribution_barplot.jpeg", format="jpeg", dpi=300)

    # Save as TeX
    tikzplotlib.save(output_dir / "arc_congestion_distribution_barplot.tex")

    plt.close()
    print("Barplot saved.".center(50))

    print("\n" + "=" * 50)
    print("Completed get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")
