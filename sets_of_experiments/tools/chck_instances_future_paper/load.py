import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import pandas as pd


def collect_instances_json(results_folder: Path, path_to_dfs: Path) -> pd.DataFrame:
    """
    Walks through all subfolders of the given directory and collects data from `results.json` files,
    flattening nested dictionaries into individual columns. Uses cache from `solutions_df.parquet` if available.

    Args:
        results_folder (Path): Root folder containing result subfolders.
        path_to_dfs (Path): Folder where the cached Parquet file should be stored/loaded.

    Returns:
        pd.DataFrame: The loaded or newly created DataFrame.
    """
    path_to_dfs.mkdir(parents=True, exist_ok=True)
    parquet_path = path_to_dfs / "instances_df.parquet"

    if parquet_path.exists():
        print(f"📦 Cached file found. Loading from: {parquet_path}")
        return pd.read_parquet(parquet_path)

    print("📂 No cache found. Walking and collecting `results.json` files...")

    rows = []
    count = 0

    for root, _, files in os.walk(results_folder):
        if "instance.json" in files:
            count += 1
            json_path = os.path.join(root, "instance.json")
            print(f"🔍 Loading ({count}): {json_path}")
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    data['instance_folder'] = os.path.basename(root)
                    rows.append(data)
            except Exception as e:
                print(f"❌ Failed to load {json_path}: {e}")

    if not rows:
        print("⚠️ No results.json files found.")
        return pd.DataFrame()

    df = pd.json_normalize(rows, sep='_')

    print(f"✅ Loaded {len(df)} instance")
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
        y="max_flow_allowed",
        x="status_quo_total_delay_hours",
        orient="h"
    )
    plt.xlabel("Status Quo Total Delay (hours)")
    plt.ylabel("Max Flow Allowed")
    plt.title("Status Quo Delay vs Congestion Level")

    plt.tight_layout()
    plt.savefig(path_to_figures / "status_quo_delay_boxplot.png", bbox_inches="tight")
    plt.close()
