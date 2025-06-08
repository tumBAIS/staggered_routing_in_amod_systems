import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import pandas as pd


def collect_jsons(results_folder: Path, path_to_dfs: Path, label: str) -> pd.DataFrame:
    """
    Walks through all subfolders of the given directory and collects data from `results.json` files,
    flattening nested dictionaries into individual columns. Uses cache from `solutions_df.parquet` if available.

    Args:
        results_folder (Path): Root folder containing result subfolders.
        path_to_dfs (Path): Folder where the cached Parquet file should be stored/loaded.
        label: Specify which kind of jsons to upload.

    Returns:
        pd.DataFrame: The loaded or newly created DataFrame.
    """
    path_to_dfs.mkdir(parents=True, exist_ok=True)
    parquet_path = path_to_dfs / f"{label}_df.parquet"

    if parquet_path.exists():
        print(f"📦 Cached file found. Loading from: {parquet_path}")
        return pd.read_parquet(parquet_path)

    print(f"📂 No cache found. Walking and collecting `{label}.json` files...")

    rows = []
    count = 0

    for root, _, files in os.walk(results_folder):
        if f"{label}.json" in files:
            count += 1
            json_path = os.path.join(root, f"{label}.json")
            print(f"🔍 Loading ({count}): {json_path}")
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    data['instance_folder'] = os.path.basename(root)
                    rows.append(data)
            except Exception as e:
                print(f"❌ Failed to load {json_path}: {e}")

    if not rows:
        print(f"⚠️ No {label}.json files found.")
        return pd.DataFrame()

    df = pd.json_normalize(rows, sep='_')

    print(f"✅ Loaded {len(df)} rows- df. ")
    print(f"💾 Saving to cache at: {parquet_path}")
    df.to_parquet(parquet_path, index=False)
    return df


def add_additional_columns_to_instances_df(instances_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds derived columns to the DataFrame for total delays in hours and delay reductions.
    Assumes delays are in seconds.
    """
    instances_df["status_quo_total_delay_hours"] = instances_df["congestion_delay_sec"] / 3600

    return instances_df


def get_boxplot_status_quo_total_delay_hours(instances_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Creates a boxplot of status quo total delay (in hours) by congestion level (max_flow_allowed).

    Args:
        instances_df (pd.DataFrame): DataFrame containing 'status_quo_total_delay_hours' and 'input_data_max_flow_allowed'.
        path_to_figures (Path): Directory where the figure will be saved.
    """
    plt.figure()
    sns.boxplot(
        data=instances_df,
        y="instance_parameters_max_flow_allowed",
        x="status_quo_total_delay_hours",
        orient="h"
    )
    plt.xlabel("Status Quo Total Delay (hours)")
    plt.ylabel("Max Flow Allowed")
    plt.title("Status Quo Delay vs Congestion Level")

    plt.tight_layout()
    os.makedirs(path_to_figures, exist_ok=True)
    plt.savefig(path_to_figures / "status_quo_delay_boxplot.png", bbox_inches="tight")
    print(f"Saved status quo total delay boxplot in {path_to_figures.resolve()}")
    plt.close()


def save_status_quo_tables_by_flow(solutions_df: pd.DataFrame, path_to_tables: Path) -> None:
    """
    Saves separate HTML tables for each unique max flow allowed value. Each table contains:
    - Day
    - Status Quo Delay (in hours)

    Args:
        solutions_df (pd.DataFrame): Must contain 'instance_parameters_day',
                                     'instance_parameters_max_flow_allowed',
                                     and 'status_quo_total_delay_hours'.
        path_to_tables (Path): Directory where HTML files will be saved.
    """
    grouped = solutions_df.groupby("instance_parameters_max_flow_allowed")

    for flow_value, group_df in grouped:
        selected = group_df[["instance_parameters_day", "status_quo_total_delay_hours"]].copy()
        selected = selected.rename(columns={
            "instance_parameters_day": "Day",
            "status_quo_total_delay_hours": "Status Quo Delay (hours)"
        })

        filename = f"status_quo_delay_flow_{flow_value}.html"
        output_path = path_to_tables / filename
        selected.to_html(output_path, index=False)


def plot_status_quo_arc_delays_per_flow(solutions_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    For each unique 'max_flow_allowed', creates a horizontal boxplot of delays on arcs per day
    from the 'status_quo_delays_on_arcs' column, which contains list of lists of floats (in minutes).

    Args:
        solutions_df (pd.DataFrame): Must contain 'instance_parameters_day',
                                     'instance_parameters_max_flow_allowed',
                                     and 'status_quo_delays_on_arcs'.
        path_to_figures (Path): Directory where the figures will be saved.
    """
    grouped = solutions_df.groupby("instance_parameters_max_flow_allowed")

    for flow_value, group_df in grouped:
        data_for_plot = []

        for _, row in group_df.iterrows():
            day = row["instance_parameters_day"]
            nested_delays = row["status_quo_delays_on_arcs_minutes"]

            # Flatten the nested list: list[list[float]] → list[float]
            flattened = [val for sublist in nested_delays for val in sublist]
            for delay in flattened:
                data_for_plot.append({"Day": day, "Delay on Arc (minutes)": delay})

        if not data_for_plot:
            continue

        plot_df = pd.DataFrame(data_for_plot)

        plt.figure(figsize=(10, max(4, len(plot_df["Day"].unique()) * 0.5)))
        plt.title(f"Status Quo Delays on Arcs — Max Flow Allowed: {flow_value}")
        plt.xlabel("Delay on Arc (minutes)")
        plt.ylabel("Day")

        # Horizontal boxplot grouped by day
        plot_df.boxplot(
            column="Delay on Arc (minutes)",
            by="Day",
            vert=False,
            grid=False
        )

        plt.suptitle("")  # Remove automatic title
        plt.tight_layout()
        os.makedirs(path_to_figures, exist_ok=True)
        output_path = path_to_figures / f"status_quo_delays_on_arcs_flow_{flow_value}.png"
        plt.savefig(output_path)
        print(f"Saved status quo delays on arcs for flow value {flow_value}.")
        plt.close()
