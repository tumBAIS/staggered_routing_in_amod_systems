from pathlib import Path
from utils.tools import deserialize
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from matplotlib.colors import LinearSegmentedColormap
from typing import Dict
import os


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


def plot_congestion_heatmap(
        G: nx.MultiDiGraph, arc_delays: Dict, ax: plt.Axes, title: str
):
    """Plot a congestion heatmap based on the total delays for arcs."""
    print(f"Plotting heatmap: {title}...")

    # Define the color map
    cmap = LinearSegmentedColormap.from_list("heatmap", ["lightgreen", "orange", "red"])
    norm = plt.Normalize(vmin=0, vmax=max(arc_delays.values(), default=1))

    for u, v, data in G.edges(data=True):
        geometry = data.get("geometry", None)
        if isinstance(geometry, LineString):
            delay = arc_delays.get((u, v), 0)  # Default delay is 0
            color = cmap(norm(delay))
            ax.plot(*geometry.xy, color=color, linewidth=2)

    # Add a colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, orientation="vertical", label="Total Delay (seconds)")

    # Set the aspect ratio to maintain the original map shape
    ax.set_aspect('equal', adjustable='datalim')
    ax.set_title(title)
    ax.axis("off")
    print(f"Heatmap '{title}' completed.")


def get_congestion_heatmap(results_df: pd.DataFrame, path_to_figures: Path, path_to_networks: Path):
    """Generate congestion heatmaps based on total arc delays."""
    print("\n" + "=" * 50)
    print("Starting Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")

    # Step 1: Ensure there is only one JSON file in path_to_networks
    print("Step 1: Validating network file...")
    network_files = list(path_to_networks.glob("*.json"))
    if len(network_files) != 1:
        raise ValueError(f"Expected 1 JSON file in {path_to_networks}, found {len(network_files)}.")
    print(f"Found network file: {network_files[0].name}")

    # Step 2: Load the network
    print("\nStep 2: Loading the network...")
    network_file = network_files[0]
    G = deserialize(network_file)
    print(f"Network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # Step 3: Split results_df into offline_df and online_df
    print("\nStep 3: Splitting results DataFrame...")
    offline_df = results_df[results_df["solver_parameters_epoch_size"] == 60]
    online_df = results_df[results_df["solver_parameters_epoch_size"] != 60]
    print(f"Offline DataFrame contains {len(offline_df)} rows.")
    print(f"Online DataFrame contains {len(online_df)} rows.")

    # Step 4: Compute total delays for each arc
    print("\nStep 4: Computing total delays for each arc...")
    offline_status_quo_delays = calculate_total_arc_delays(
        offline_df, delay_column="status_quo_delays_on_arcs", mapping_column="arc_to_node_mapping"
    )
    offline_solution_delays = calculate_total_arc_delays(
        offline_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
    )
    online_solution_delays = calculate_total_arc_delays(
        online_df, delay_column="solution_delays_on_arcs", mapping_column="arc_to_node_mapping"
    )

    # Step 5: Plot and save separate heatmaps
    print("\nStep 5: Generating and saving separate heatmaps...")
    output_dir = path_to_figures / "heatmaps"
    os.makedirs(output_dir, exist_ok=True)

    # Offline Status Quo
    fig, ax = plt.subplots(figsize=(6, 6))
    plot_congestion_heatmap(
        G,
        offline_status_quo_delays,
        ax=ax,
        title="Offline Status Quo",
    )
    plt.tight_layout()
    plt.savefig(output_dir / "offline_status_quo_heatmap.jpeg", dpi=300, format="jpeg")
    print(f"Saved: {output_dir / 'offline_status_quo_heatmap.jpeg'}")
    plt.close()

    # Offline Solution
    fig, ax = plt.subplots(figsize=(6, 6))
    plot_congestion_heatmap(
        G,
        offline_solution_delays,
        ax=ax,
        title="Offline Solution",
    )
    plt.tight_layout()
    plt.savefig(output_dir / "offline_solution_heatmap.jpeg", dpi=300, format="jpeg")
    print(f"Saved: {output_dir / 'offline_solution_heatmap.jpeg'}")
    plt.close()

    # Online Solution
    fig, ax = plt.subplots(figsize=(6, 6))
    plot_congestion_heatmap(
        G,
        online_solution_delays,
        ax=ax,
        title="Online Solution",
    )
    plt.tight_layout()
    plt.savefig(output_dir / "online_solution_heatmap.jpeg", dpi=300, format="jpeg")
    print(f"Saved: {output_dir / 'online_solution_heatmap.jpeg'}")
    plt.close()

    print("\n" + "=" * 50)
    print("Completed Congestion Heatmap Generation".center(50))
    print("=" * 50 + "\n")
