import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import tikzplotlib
from pprint import pprint


def print_dict_info(name, d):
    if d:
        values = np.array(list(d.values()))
        values.sort()

        def percentile(p):
            return values[int(len(values) * p / 100)]

        stats = {
            "Count": len(values),
            "Min": values[0],
            "Max": values[-1],
            "Mean": values.mean(),
            "Median (50%)": percentile(50),
            "70th Percentile": percentile(70),
            "90th Percentile": percentile(90),
            "95th Percentile": percentile(95),
            "98th Percentile": percentile(98),
            "99th Percentile": percentile(99),
        }

        print(f"\n{name} Statistics:")
        pprint(stats, sort_dicts=False)


def print_congestion_statistics(unc_delays, off_delays, on_delays):
    # Identify arcs based on congestion changes
    unc_but_not_off = {arc for arc in unc_delays if unc_delays[arc] > 0 and off_delays.get(arc, 0) == 0}
    unc_but_not_on = {arc for arc in unc_delays if unc_delays[arc] > 0 and on_delays.get(arc, 0) == 0}
    off_but_not_unc = {arc for arc in off_delays if off_delays[arc] > 0 and unc_delays.get(arc, 0) == 0}
    on_but_not_unc = {arc for arc in on_delays if on_delays[arc] > 0 and unc_delays.get(arc, 0) == 0}

    # Print results clearly
    print("\nCongestion Analysis Results".center(50, "="))
    print(f"Number of arcs congested in UNC but not in OFF: {len(unc_but_not_off)}")
    print(f"Number of arcs congested in UNC but not in ON: {len(unc_but_not_on)}")
    print(f"Number of arcs congested in OFF but not in UNC: {len(off_but_not_unc)}")
    print(f"Number of arcs congested in ON but not in UNC: {len(on_but_not_unc)}")
    print(f"Decrease in number of congested arcs from UNC to OFF: {len(unc_but_not_off) - len(off_but_not_unc)}")
    print(f"Decrease in number of congested arcs from UNC to ON: {len(unc_but_not_on) - len(on_but_not_unc)}")
    print("=" * 50)


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

        # Print how congestion is shifted among different algo versions
        print_congestion_statistics(unc_delays, off_delays, on_delays)

        # Filter out arcs with a maximum delay of at most 1e-1 in all barplots
        all_arcs = set(unc_delays.keys()) | set(off_delays.keys()) | set(on_delays.keys())
        filtered_arcs = {arc for arc in all_arcs if max(unc_delays.get(arc, 0), off_delays.get(arc, 0),
                                                        on_delays.get(arc, 0)) > 1e-1}

        unc_delays = {arc: delay for arc, delay in unc_delays.items() if arc in filtered_arcs}
        off_delays = {arc: delay for arc, delay in off_delays.items() if arc in filtered_arcs}
        on_delays = {arc: delay for arc, delay in on_delays.items() if arc in filtered_arcs}

        # Print info
        print_dict_info("unc_delays", unc_delays)
        print_dict_info("off_delays", off_delays)
        print_dict_info("on_delays", on_delays)

        # Adjust bins: include the 0-1e-1 bin explicitly
        bins = np.concatenate(([0, 1e-1], np.arange(1, 101, 10)))  # Include 0 to 1e-1 bin
        bin_labels = ["0"] + [f"{int(bins[i]) + 9}" for i in range(2, len(bins))]

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
        #
        # plt.legend(loc="upper right", frameon=True, framealpha=1, facecolor="white", edgecolor="black",
        #            handlelength=2, handleheight=1.5, fontsize=10)  # Ensure proper legend size and rectangles
        plt.tight_layout()

        # Save plot
        output_dir = path_to_figures / "arc_congestion_distribution"
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"arc_congestion_distribution_barplot_{label.lower()}"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)

        with open(output_dir / f"{file_name}.tex", "w") as tex_file:
            tex_content = tikzplotlib.get_tikz_code()

            # Remove log basis y
            tex_content = tex_content.replace("log basis y={10},", "")

            # Correct bar heights to start from zero
            tex_content = tex_content.replace("ycomb", "")

            # Explicitly set axis dimensions
            tex_content = tex_content.replace(
                "\\begin{axis}[",
                "\\begin{axis}[width=\\columnwidth, height=\\TotalDelayBarplotsHeight,"
            )

            # Remove all lines related to legends
            lines = tex_content.split("\n")
            tex_content = "\n".join(
                line for line in lines if not ("\\addlegendentry" in line or "\\addlegendimage" in line)
            )

            # Write the modified TikZ code to the file
            tex_file.write(tex_content)

        plt.close()
        print(f"{label} barplot saved.".center(50))

    # Generate plots for LC and HC
    create_barplot_for_congestion(lc_df, "LC")
    create_barplot_for_congestion(hc_df, "HC")

    print("\n" + "=" * 50)
    print("Completed get_arc_congestion_distribution_barplot".center(50))
    print("=" * 50 + "\n")
