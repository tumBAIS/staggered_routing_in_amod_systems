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


def calculate_arc_delay_counts(results_df: pd.DataFrame, delay_column: str, mapping_column: str) -> Dict:
    """
    Calculate how many trips experience a delay greater than 1e-4 on each arc.
    Essentially, we count the number of 'delayed trips' per arc.
    """
    print(f"\nCalculating delayed trip counts for arcs using column '{delay_column}'...")
    arc_delay_counts = {}
    threshold = 1e-4
    for _, row in results_df.iterrows():
        delays_on_arcs = row[delay_column]
        arc_mapping = row[mapping_column]
        for trip, delays in zip(row["instance_trip_routes"], delays_on_arcs):
            for arc, delay in zip(trip, delays):
                if arc in arc_mapping and delay > threshold:
                    node_pair = arc_mapping[arc]
                    if node_pair not in arc_delay_counts:
                        arc_delay_counts[node_pair] = 0
                    arc_delay_counts[node_pair] += 1
    print(f"Completed counting delayed trips. Found counts for {len(arc_delay_counts)} arcs.")
    return arc_delay_counts


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


def print_delay_count_statistics(counts: Dict):
    """Print distributional statistics for delayed trip counts."""
    count_values = np.array(list(counts.values()))
    print("\nDelayed Trip Count Statistics:")
    print(f"Min: {np.min(count_values):d}")
    print(f"Max: {np.max(count_values):d}")
    print(f"Mean: {np.mean(count_values):.2f}")
    print(f"Median: {np.median(count_values):.2f}")
    for percentile in [95, 96, 97, 98, 99]:
        print(f"{percentile}th Percentile: {np.percentile(count_values, percentile):.2f}")


def get_congestion_heatmap_total_delay(results_df: pd.DataFrame, path_to_figures: Path, path_to_networks: Path):
    """Generate separate congestion heatmaps for LC and HC congestion levels, and also generate
    plots for delayed trip counts."""
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

        # Print delay statistics if annotating
        if annotate:
            print(f"\nStatistics for {label} - UNC:")
            print_delay_statistics(offline_status_quo_delays)

            print(f"\nStatistics for {label} - OFF:")
            print_delay_statistics(offline_solution_delays)

            print(f"\nStatistics for {label} - ON:")
            print_delay_statistics(online_solution_delays)

        # Determine a shared color scale for delays
        all_delays = list(offline_status_quo_delays.values()) + \
                     list(offline_solution_delays.values()) + \
                     list(online_solution_delays.values())
        max_delay = np.percentile(list(offline_status_quo_delays.values()),
                                  max_percentile) if offline_status_quo_delays and max_percentile < 100 else max(
            all_delays, default=1)
        cmap = LinearSegmentedColormap.from_list("heatmap", ["green", "orange", "red"])
        norm = plt.Normalize(vmin=0, vmax=max_delay)

        # Calculate delayed trip counts
        offline_status_quo_counts = calculate_arc_delay_counts(
            offline_df, delay_column="status_quo_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )
        offline_solution_counts = calculate_arc_delay_counts(
            offline_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )
        online_solution_counts = calculate_arc_delay_counts(
            online_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
        )

        # Print delayed trip count statistics if annotating
        if annotate:
            print(f"\nStatistics for {label} - UNC Counts:")
            print_delay_count_statistics(offline_status_quo_counts)

            print(f"\nStatistics for {label} - OFF Counts:")
            print_delay_count_statistics(offline_solution_counts)

            print(f"\nStatistics for {label} - ON Counts:")
            print_delay_count_statistics(online_solution_counts)

        # Determine color scale for counts
        all_counts = list(offline_status_quo_counts.values()) + \
                     list(offline_solution_counts.values()) + \
                     list(online_solution_counts.values())
        max_count = np.percentile(list(offline_status_quo_counts.values()),
                                  max_percentile) if offline_status_quo_counts and max_percentile < 100 else max(
            all_counts, default=1)
        count_cmap = LinearSegmentedColormap.from_list("count_heatmap", ["white", "blue", "purple"])
        count_norm = plt.Normalize(vmin=0, vmax=max_count)

        rotation_angle = 29
        origin = (0, 0)

        def plot_background_map(ax):
            """Plot the full Manhattan map in green."""
            if not G_full:
                return
            for u, v, edge_data in G_full.edges(data=True):
                geometry = edge_data.get("geometry", None)
                if isinstance(geometry, LineString):
                    rotated_geometry = rotate_geometry(geometry, angle=rotation_angle, origin=origin)
                    ax.plot(*rotated_geometry.xy, color="green", linewidth=0.25, zorder=0)

        def style_axes(axs):
            for ax in axs:
                ax.set_aspect("equal", adjustable="box")
                ax.set_box_aspect(3.5)  # Adjust as needed for desired narrowness
                ax.set_xticks([])
                ax.set_yticks([])
                ax.tick_params(axis='both', which='both', length=0)
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color('black')
                    spine.set_linewidth(1.0)

        def plot_data(datasets, title, cmap, norm, output_folder_name, suffix):
            # datasets = [UNC_data, OFF_data, ON_data]
            fig, axs = plt.subplots(1, 3, figsize=(3, 3), gridspec_kw={'width_ratios': [1, 1, 1], 'wspace': 0})

            # UNC
            ax = axs[0]
            plot_background_map(ax)
            if annotate:
                ax.set_title("UNC", pad=10)
            for u, v, edge_data in G.edges(data=True):
                val = datasets[0].get((u, v), 0)
                if val > 0 and isinstance(edge_data.get("geometry", None), LineString):
                    rotated_geometry = rotate_geometry(edge_data["geometry"], angle=rotation_angle, origin=origin)
                    ax.plot(*rotated_geometry.xy, color=cmap(norm(val)), linewidth=0.25, zorder=10000)

            # OFF
            ax = axs[1]
            plot_background_map(ax)
            if annotate:
                ax.set_title("OFF", pad=10)
            for u, v, edge_data in G.edges(data=True):
                val = datasets[1].get((u, v), 0)
                if val > 0 and isinstance(edge_data.get("geometry", None), LineString):
                    rotated_geometry = rotate_geometry(edge_data["geometry"], angle=rotation_angle, origin=origin)
                    ax.plot(*rotated_geometry.xy, color=cmap(norm(val)), linewidth=0.25, zorder=10000)

            # ON
            ax = axs[2]
            plot_background_map(ax)
            if annotate:
                ax.set_title("ON", pad=10)
            for u, v, edge_data in G.edges(data=True):
                val = datasets[2].get((u, v), 0)
                if val > 0 and isinstance(edge_data.get("geometry", None), LineString):
                    rotated_geometry = rotate_geometry(edge_data["geometry"], angle=rotation_angle, origin=origin)
                    ax.plot(*rotated_geometry.xy, color=cmap(norm(val)), linewidth=0.25, zorder=10000)

            style_axes(axs)

            # Add colorbar
            cbar_ax = fig.add_axes([0.8, 0.11, 0.02, 0.77])
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, cax=cbar_ax, orientation="vertical")
            if annotate:
                if "delayed_trips" in output_folder_name:
                    cbar.set_label("Delayed Trips Count")
                else:
                    cbar.set_label(r"$\Omega_a$")
            else:
                cbar.ax.tick_params(axis='y', which='both', labelsize=0, length=0, width=0, labelleft=False,
                                    labelright=False)
                cbar.set_ticks([])
                cbar.ax.set_yticklabels([])

            output_dir = path_to_figures / output_folder_name
            os.makedirs(output_dir, exist_ok=True)
            fig.subplots_adjust(left=0.025, right=.8)
            plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}_{suffix}.jpeg", dpi=300, format="jpeg")
            plt.savefig(output_dir / f"congestion_heatmap_{label.lower()}_{suffix}.pdf", dpi=300, format="pdf")
            print(f"Saved: {output_dir / f'congestion_heatmap_{label.lower()}_{suffix}.jpeg'}")
            plt.close()

        # Plot original delay data
        plot_data([offline_status_quo_delays, offline_solution_delays, online_solution_delays],
                  "Delays", cmap, norm, "heatmaps", "annotated" if annotate else "no_annotations")

        # Plot delayed trips count data
        plot_data([offline_status_quo_counts, offline_solution_counts, online_solution_counts],
                  "Counts", count_cmap, count_norm, "heatmaps_delayed_trips",
                  "annotated" if annotate else "no_annotations")

    # Generate heatmaps for LC and HC
    calculate_and_plot_heatmap(lc_df, "LC", annotate=True, max_percentile=99)
    calculate_and_plot_heatmap(lc_df, "LC", annotate=False, max_percentile=99)
    calculate_and_plot_heatmap(hc_df, "HC", annotate=True, max_percentile=99)
    calculate_and_plot_heatmap(hc_df, "HC", annotate=False, max_percentile=99)

    print("\n" + "=" * 50)
    print("Completed Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")
