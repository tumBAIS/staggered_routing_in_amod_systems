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

        # Create barplot
        bar_width = 0.3
        x = np.arange(len(bins) - 1)  # X positions for the bars

        plt.figure(figsize=(8, 5))
        plt.grid(axis="y", linestyle="--", color="gray", alpha=0.7, which="major", zorder=0)
        plt.grid(axis="y", linestyle="--", color="lightgray", alpha=0.4, which="minor", zorder=0)

        # Define minimalistic and professional colors
        unc_color = "#1f77b4"  # Blue
        off_color = "#ff7f0e"  # Orange
        on_color = "#2ca02c"  # Green

        plt.bar(x - bar_width, unc_freq, width=bar_width, color=unc_color, edgecolor="black", label="UNC", zorder=2)
        plt.bar(x, off_freq, width=bar_width, color=off_color, edgecolor="black", label="OFF", zorder=2)
        plt.bar(x + bar_width, on_freq, width=bar_width, color=on_color, edgecolor="black", label="ON", zorder=2)

        plt.yscale("log")
        plt.ylim(bottom=1e1, top=4000)  # Ensure bars start at bottom of y-axis
        plt.xlabel(r"$\mathcal{E}_a$ [min]")  # Updated to minutes
        plt.ylabel("Observations")

        # Update xticks to include labels
        plt.xticks(x, bin_labels, rotation=0)

        plt.legend(loc="upper right", frameon=True, framealpha=1, facecolor="white", edgecolor="black",
                   handlelength=2, handleheight=1.5, fontsize=10)  # Ensure proper legend size and rectangles
        plt.tight_layout()

        # Save plot
        output_dir = path_to_figures / "arc_congestion_distribution"
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"arc_congestion_distribution_barplot_{label.lower()}"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)

        with open(output_dir / f"{file_name}.tex", "w") as tex_file:
            tex_content = tikzplotlib.get_tikz_code()
            tex_content = tex_content.replace("log basis y={10},", "")  # Remove log basis y
            tex_content = tex_content.replace("ybar,ybar legend",
                                              "rectangle,fill=legendfill")  # Proper legend rectangles
            tex_content = tex_content.replace("ycomb", "")  # Correct bar heights to start from zero
            tex_content = tex_content.replace(
                "\\begin{axis}[",
                "\\begin{axis}[width=\\columnwidth, height=4.5cm,"  # Explicitly set axis dimensions
            )
            tex_file.write(tex_content)

        plt.close()
        print(f"{label} barplot saved.".center(50))

    # Generate plots for LC and HC
    create_barplot_for_congestion(lc_df, "LC")
    create_barplot_for_congestion(hc_df, "HC")

    print("\n" + "=" * 50)
    print("Completed get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")
