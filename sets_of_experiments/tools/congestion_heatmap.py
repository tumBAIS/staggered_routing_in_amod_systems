from pathlib import Path
from utils.tools import deserialize
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from matplotlib.colors import LinearSegmentedColormap
from typing import Dict
import os
import warnings
from shapely.affinity import rotate
import numpy as np

warnings.filterwarnings("ignore", message="This figure includes Axes that are not compatible with tight_layout")


def rotate_geometry(geometry, angle, origin=(0, 0)):
    """Rotate a Shapely geometry by a given angle around the specified origin."""
    return rotate(geometry, angle, origin=origin, use_radians=False)


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
                    arc_delays[node_pair] += delay / 60  # Convert to minutes
    print(f"Completed delay calculations. Found delays for {len(arc_delays)} arcs.")
    return arc_delays


def print_delay_statistics(delays: Dict):
    """Print distributional statistics for delays."""
    delay_values = np.array(list(delays.values()))
    print("\nDelay Statistics:")
    print(f"Min: {np.min(delay_values):.2f} minutes")
    print(f"Max: {np.max(delay_values):.2f} minutes")
    print(f"Mean: {np.mean(delay_values):.2f} minutes")
    print(f"Median: {np.median(delay_values):.2f} minutes")
    for percentile in [95, 96, 97, 98, 99]:
        print(f"{percentile}th Percentile: {np.percentile(delay_values, percentile):.2f} minutes")


def get_congestion_heatmap(results_df: pd.DataFrame, path_to_figures: Path, path_to_networks: Path):
    """Generate separate congestion heatmaps for LC and HC congestion levels."""
    print("\n" + "=" * 50)
    print("Starting Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")

    # Step 1: Ensure there is a JSON network file and check for full_manhattan.json
    print("Step 1: Validating network files...".center(50))
    network_files = list(path_to_networks.glob("*.json"))
    if len(network_files) < 1:
        raise ValueError(f"Expected at least 1 JSON file in {path_to_networks}, found none.")

    full_manhattan_file = path_to_networks / "full_manhattan.json"
    full_manhattan_exists = full_manhattan_file.exists()

    # Load the primary network
    primary_network_file = next((f for f in network_files if f != full_manhattan_file), None)
    if not primary_network_file:
        raise ValueError(f"No primary network file found in {path_to_networks}.")
    print(f"Primary network file: {primary_network_file.name}")
    print(f"Full Manhattan file exists: {full_manhattan_exists}")

    # Step 2: Load the networks
    print("\nStep 2: Loading the networks...".center(50))
    G = deserialize(primary_network_file)
    print(f"Primary network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    G_full = deserialize(full_manhattan_file) if full_manhattan_exists else None
    if G_full:
        print(f"Full Manhattan network loaded with {len(G_full.nodes)} nodes and {len(G_full.edges)} edges.")

    # Step 3: Split DataFrame by congestion levels
    print("\nStep 3: Splitting DataFrame by congestion levels...".center(50))
    lc_df = results_df[results_df["congestion_level"] == "LC"]
    hc_df = results_df[results_df["congestion_level"] == "HC"]
    print(f"LC DataFrame contains {len(lc_df)} rows.")
    print(f"HC DataFrame contains {len(hc_df)} rows.")

    # Helper function to calculate total delays and plot heatmaps
    def calculate_and_plot_heatmap(data_df, label, annotate=True, max_percentile: int = 100):
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

        # Print delay statistics
        if annotate:
            print(f"\nStatistics for {label} - UNC:")
            print_delay_statistics(offline_status_quo_delays)

            print(f"\nStatistics for {label} - OFF:")
            print_delay_statistics(offline_solution_delays)

            print(f"\nStatistics for {label} - ON:")
            print_delay_statistics(online_solution_delays)

        # Determine a shared color scale
        all_delays = list(offline_status_quo_delays.values()) + \
                     list(offline_solution_delays.values()) + \
                     list(online_solution_delays.values())
        max_delay = np.percentile(list(offline_status_quo_delays.values()),
                                  max_percentile) if max_percentile < 100 else max(
            all_delays, default=1)
        cmap = LinearSegmentedColormap.from_list("heatmap", ["green", "orange", "red"])
        norm = plt.Normalize(vmin=0, vmax=max_delay)

        # Rotation parameters
        rotation_angle = 29  # Adjust angle as necessary for perfect vertical alignment
        origin = (0, 0)

        # Generate heatmap
        print("\nGenerating heatmap...".center(50))
        fig, axs = plt.subplots(1, 3, figsize=(3, 3), gridspec_kw={'width_ratios': [1, 1, 1], 'wspace': 0})

        def plot_background_map(ax):
            """Plot the full Manhattan map in green."""
            if not G_full:
                return
            for u, v, edge_data in G_full.edges(data=True):
                geometry = edge_data.get("geometry", None)
                if isinstance(geometry, LineString):
                    rotated_geometry = rotate_geometry(geometry, angle=rotation_angle, origin=origin)
                    ax.plot(*rotated_geometry.xy, color="green", linewidth=0.25, zorder=0)

        def plot_heatmap(data, ax, title):
            """Plot a single heatmap for a specific dataset."""
            plot_background_map(ax)  # Plot the background map first
            sorted_edges = sorted(
                G.edges(data=True),
                key=lambda edge: data.get((edge[0], edge[1]), 0),
            )
            if annotate:
                ax.set_title(title, pad=10)

            for u, v, edge_data in sorted_edges:
                geometry = edge_data.get("geometry", None)
                delay = data.get((u, v), 0)
                if isinstance(geometry, LineString) and delay > 0:  # Exclude zero-delay arcs
                    rotated_geometry = rotate_geometry(geometry, angle=rotation_angle, origin=origin)
                    color = cmap(norm(delay))
                    ax.plot(*rotated_geometry.xy, color=color, linewidth=0.25, zorder=10000)
            for ax in axs:
                # Force the axis to adjust the box (not just the data limits)
                ax.set_aspect("equal", adjustable="box")
                # Make the box taller and narrower by increasing the height-to-width ratio.
                # For instance, a value greater than 1 will create a tall, narrow box.
                ax.set_box_aspect(3.5)  # Adjust this ratio until you get the desired width

                # Remove ticks but keep the spines
                ax.set_xticks([])
                ax.set_yticks([])
                ax.tick_params(axis='both', which='both', length=0)
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color('black')
                    spine.set_linewidth(1.0)

        plot_heatmap(offline_status_quo_delays, axs[0], "UNC")
        plot_heatmap(offline_solution_delays, axs[1], "OFF")
        plot_heatmap(online_solution_delays, axs[2], "ON")

        # Add colorbar
        cbar_ax = fig.add_axes([0.8, 0.11, 0.02, 0.77])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, cax=cbar_ax, orientation="vertical")
        if annotate:
            cbar.set_label(r"$\Omega_a$ [minutes]")
        else:
            cbar.ax.tick_params(axis='y', which='both', labelsize=0, length=0, width=0, labelleft=False,
                                labelright=False)
            # Remove tick marks and labels
            cbar.set_ticks([])
            # Optionally, remove the tick labels as well
            cbar.ax.set_yticklabels([])

        # Save the heatmap
        output_dir = path_to_figures / "heatmaps"
        os.makedirs(output_dir, exist_ok=True)
        fig.subplots_adjust(left=0.025, right=.8)
        suffix = "annotated" if annotate else "no_annotations"
        plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}_{suffix}.jpeg", dpi=300, format="jpeg")
        plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}_{suffix}.pdf", dpi=300, format="pdf")
        print(f"Saved: {output_dir / f'congestion_heatmap_{label.lower()}_{suffix}.jpeg'}")
        plt.close()

    # Generate heatmaps for LC and HC
    calculate_and_plot_heatmap(lc_df, "LC", annotate=True, max_percentile=99)
    calculate_and_plot_heatmap(lc_df, "LC", annotate=False, max_percentile=99)
    calculate_and_plot_heatmap(hc_df, "HC", annotate=True, max_percentile=99)
    calculate_and_plot_heatmap(hc_df, "HC", annotate=False, max_percentile=99)

    print("\n" + "=" * 50)
    print("Completed Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")
