from pathlib import Path
from utils.tools import deserialize
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from matplotlib.colors import LinearSegmentedColormap
from typing import Dict
import os
import warnings

warnings.filterwarnings("ignore", message="This figure includes Axes that are not compatible with tight_layout")


def calculate_total_arc_delays(results_df: pd.DataFrame, delay_column: str, mapping_column: str) -> Dict:
    """Calculate the total delay for each arc across all instances."""
    print(f"\nCalculating total delays for arcs using column '{delay_column}'...")
    arc_delays = {}
    for _, row in results_df.iterrows():
        delays_on_arcs = row[delay_column]
        arc_mapping = row[mapping_column]
        for trip, delays in zip(row["instance_trip_routes"], delays_on_arcs):
            for arc, delay in zip(trip, delays):
                if arc in arc_mapping:
                    node_pair = arc_mapping[arc]
                    if node_pair not in arc_delays:
                        arc_delays[node_pair] = 0
                    arc_delays[node_pair] += delay
    print(f"Completed delay calculations. Found delays for {len(arc_delays)} arcs.")
    return arc_delays


def get_congestion_heatmap(results_df: pd.DataFrame, path_to_figures: Path, path_to_networks: Path):
    """Generate separate congestion heatmaps for LC and HC congestion levels."""
    print("\n" + "=" * 50)
    print("Starting Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")

    # Step 1: Ensure there is only one JSON file in path_to_networks
    print("Step 1: Validating network file...".center(50))
    network_files = list(path_to_networks.glob("*.json"))
    if len(network_files) != 1:
        raise ValueError(f"Expected 1 JSON file in {path_to_networks}, found {len(network_files)}.")
    print(f"Found network file: {network_files[0].name}")

    # Step 2: Load the network
    print("\nStep 2: Loading the network...".center(50))
    network_file = network_files[0]
    G = deserialize(network_file)
    print(f"Network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # Step 3: Split DataFrame by congestion levels
    print("\nStep 3: Splitting DataFrame by congestion levels...".center(50))
    lc_df = results_df[results_df["congestion_level"] == "LC"]
    hc_df = results_df[results_df["congestion_level"] == "HC"]
    print(f"LC DataFrame contains {len(lc_df)} rows.")
    print(f"HC DataFrame contains {len(hc_df)} rows.")

    # Helper function to calculate total delays and plot heatmaps
    def calculate_and_plot_heatmap(data_df, label):
        print(f"\nProcessing {label} data...".center(50))

        # Split into offline and online
        offline_df = data_df[data_df["solver_parameters_epoch_size"] == 60]
        online_df = data_df[data_df["solver_parameters_epoch_size"] != 60]

        # Calculate total delays for each arc
        offline_status_quo_delays = calculate_total_arc_delays(
            offline_df, delay_column="status_quo_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )
        offline_solution_delays = calculate_total_arc_delays(
            offline_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )
        online_solution_delays = calculate_total_arc_delays(
            online_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )

        # Determine a shared color scale
        all_delays = list(offline_status_quo_delays.values()) + \
                     list(offline_solution_delays.values()) + \
                     list(online_solution_delays.values())
        max_delay = max(all_delays, default=1)
        cmap = LinearSegmentedColormap.from_list("heatmap", ["lightgreen", "orange", "red"])
        norm = plt.Normalize(vmin=0, vmax=max_delay)

        # Generate heatmap
        print("\nGenerating heatmap...".center(50))
        fig, axs = plt.subplots(1, 3, figsize=(14, 3), gridspec_kw={'width_ratios': [1, 1, 1], 'wspace': -0.05})

        def plot_heatmap(data, ax, title):
            """Plot a single heatmap for a specific dataset."""
            sorted_edges = sorted(
                G.edges(data=True),
                key=lambda edge: data.get((edge[0], edge[1]), 0),
            )
            for u, v, edge_data in sorted_edges:
                geometry = edge_data.get("geometry", None)
                if isinstance(geometry, LineString):
                    delay = data.get((u, v), 0)
                    color = cmap(norm(delay))
                    ax.plot(*geometry.xy, color=color, linewidth=1)
            ax.set_aspect("equal", adjustable="datalim")
            ax.axis("off")
            ax.set_title(title, pad=10)

        plot_heatmap(offline_status_quo_delays, axs[0], "UNC")
        plot_heatmap(offline_solution_delays, axs[1], "OFF")
        plot_heatmap(online_solution_delays, axs[2], "ON")

        # Add colorbar
        cbar_ax = fig.add_axes([0.93, 0.165, 0.02, 0.68])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, cax=cbar_ax, orientation="vertical")
        cbar.set_label(r"$\Omega_a$ [seconds]")

        # Save the heatmap
        output_dir = path_to_figures / "heatmaps"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}.jpeg", dpi=300, format="jpeg")
        plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}.pdf", dpi=300, format="pdf")
        print(f"Saved: {output_dir / f'congestion_heatmap_{label.lower()}.jpeg'}")
        plt.close()

    # Generate heatmaps for LC and HC
    calculate_and_plot_heatmap(lc_df, "LC")
    calculate_and_plot_heatmap(hc_df, "HC")

    print("\n" + "=" * 50)
    print("Completed Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")
