import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import tikzplotlib


def get_arc_congestion_distribution_barplot(results_df: pd.DataFrame, path_to_figures: Path,
                                            verbose: bool = False) -> None:
    """
    Generate barplots for arc congestion distributions for UNC, OFF, and ON scenarios,
    separately for LC and HC congestion levels, with optional verbose output.
    """
    print("\n" + "=" * 50)
    print("Starting get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")

    # Step 1: Split DataFrame by congestion levels
    print("Step 1: Splitting the DataFrame by congestion levels...".center(50))
    lc_df = results_df[results_df["congestion_level"] == "LC"]
    hc_df = results_df[results_df["congestion_level"] == "HC"]
    print(f"LC DataFrame contains {len(lc_df)} rows.".center(50))
    print(f"HC DataFrame contains {len(hc_df)} rows.".center(50))

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
                        arc_delays[node_pair] += delay / 60  # Convert delay to minutes
        return arc_delays

    def create_barplot_for_congestion(data, label):
        print(f"\nProcessing {label} data...".center(50))
        offline_df = data[data["solver_parameters_epoch_size"] == 60]
        online_df = data[data["solver_parameters_epoch_size"] != 60]

        # Calculate total delays for UNC, OFF, and ON
        unc_delays = calculate_arc_delays(offline_df, "status_quo_delays_on_arcs", "arc_to_node_mapping")
        off_delays = calculate_arc_delays(offline_df, "solution_delays_on_arcs", "arc_to_node_mapping")
        on_delays = calculate_arc_delays(online_df, "solution_delays_on_arcs", "arc_to_node_mapping")

        # Filter out arcs with a maximum delay of at most 1e-1 in all barplots
        all_arcs = set(unc_delays.keys()) | set(off_delays.keys()) | set(on_delays.keys())
        filtered_arcs = {arc for arc in all_arcs if max(unc_delays.get(arc, 0), off_delays.get(arc, 0),
                                                        on_delays.get(arc, 0)) > 1e-1}

        unc_delays = {arc: delay for arc, delay in unc_delays.items() if arc in filtered_arcs}
        off_delays = {arc: delay for arc, delay in off_delays.items() if arc in filtered_arcs}
        on_delays = {arc: delay for arc, delay in on_delays.items() if arc in filtered_arcs}

        # Adjust bins: include the 0-1e-1 bin explicitly
        bins = np.concatenate(([0, 1e-1], np.arange(2, 34, 2)))  # Include 0 to 1e-1 bin
        bin_labels = ["0"] + [f"{int(bins[i])}" for i in range(2, len(bins))]

        unc_values = list(unc_delays.values())
        off_values = list(off_delays.values())
        on_values = list(on_delays.values())

        unc_freq, _ = np.histogram(unc_values, bins=bins)
        off_freq, _ = np.histogram(off_values, bins=bins)
        on_freq, _ = np.histogram(on_values, bins=bins)

        if verbose:
            # Print detailed information about the barplots
            print(f"\n{label} Barplot Information:")
            for i in range(len(bins) - 1):
                # Filter values falling into the current bin
                unc_in_bin = [val for val in unc_values if bins[i] <= val < bins[i + 1]]
                off_in_bin = [val for val in off_values if bins[i] <= val < bins[i + 1]]
                on_in_bin = [val for val in on_values if bins[i] <= val < bins[i + 1]]

                # Calculate min and max for the current bin
                unc_min, unc_max = (min(unc_in_bin), max(unc_in_bin)) if unc_in_bin else (None, None)
                off_min, off_max = (min(off_in_bin), max(off_in_bin)) if off_in_bin else (None, None)
                on_min, on_max = (min(on_in_bin), max(on_in_bin)) if on_in_bin else (None, None)

                # Format values (round to 4 decimals for clarity)
                def format_value(val):
                    return f"{val:.2f}" if val is not None else "None"

                unc_in_bin = [format_value(v) for v in unc_in_bin]
                off_in_bin = [format_value(v) for v in off_in_bin]
                on_in_bin = [format_value(v) for v in on_in_bin]

                unc_min, unc_max = format_value(unc_min), format_value(unc_max)
                off_min, off_max = format_value(off_min), format_value(off_max)
                on_min, on_max = format_value(on_min), format_value(on_max)

                # Print bin details
                print(f"  Bin [{bins[i]}, {bins[i + 1]}):")
                print(f"    UNC: {unc_freq[i]} observations")
                print(f"      Sample data: {unc_in_bin[:5]}")  # Print up to 5 sample points
                print(f"      Min: {unc_min}, Max: {unc_max}")
                print(f"    OFF: {off_freq[i]} observations")
                print(f"      Sample data: {off_in_bin[:5]}")
                print(f"      Min: {off_min}, Max: {off_max}")
                print(f"    ON: {on_freq[i]} observations")
                print(f"      Sample data: {on_in_bin[:5]}")
                print(f"      Min: {on_min}, Max: {on_max}")

        # Create barplot
        bar_width = 0.3
        x = np.arange(len(bins) - 1)  # X positions for the bars

        plt.figure(figsize=(8, 5))
        plt.grid(axis="y", linestyle="--", color="gray", alpha=0.7, which="major", zorder=0)
        plt.grid(axis="y", linestyle="--", color="lightgray", alpha=0.4, which="minor", zorder=0)

        plt.bar(x - bar_width, unc_freq, width=bar_width, color="gray", edgecolor="black", label="UNC", hatch="/",
                zorder=2)
        plt.bar(x, off_freq, width=bar_width, color="white", edgecolor="black", label="OFF", hatch=".", zorder=2)
        plt.bar(x + bar_width, on_freq, width=bar_width, color="lightgray", edgecolor="black", label="ON", hatch="\\",
                zorder=2)

        plt.yscale("log")
        plt.ylim(top=4000)  # Set y-axis maximum to 3000
        plt.xlabel(r"$\mathcal{E}_a$ [min]")  # Updated to minutes
        plt.ylabel("Observations")

        # Update xticks to include labels
        plt.xticks(x, bin_labels, rotation=0)

        plt.legend(loc="upper right", frameon=True, framealpha=1, facecolor="white", edgecolor="black")
        plt.tight_layout()

        # Save plot
        output_dir = path_to_figures / "arc_congestion_distribution"
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"arc_congestion_distribution_barplot_{label.lower()}"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)
        tikzplotlib.save(output_dir / f"{file_name}.tex")

        plt.close()
        print(f"{label} barplot saved.".center(50))

    # Generate plots for LC and HC
    create_barplot_for_congestion(lc_df, "LC")
    create_barplot_for_congestion(hc_df, "HC")

    print("\n" + "=" * 50)
    print("Completed get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")
