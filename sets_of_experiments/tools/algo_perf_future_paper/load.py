import os
import json
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

import pandas as pd


def collect_results_json(results_folder: Path, path_to_dfs: Path) -> pd.DataFrame:
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
    parquet_path = path_to_dfs / "solutions_df.parquet"

    if parquet_path.exists():
        print(f"📦 Cached file found. Loading from: {parquet_path}")
        return pd.read_parquet(parquet_path)

    print("📂 No cache found. Walking and collecting `results.json` files...")

    rows = []
    count = 0

    for root, _, files in os.walk(results_folder):
        if "results.json" in files:
            count += 1
            json_path = os.path.join(root, "results.json")
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

    print(f"✅ Loaded {len(df)} results with columns: {list(df.columns)}")
    print(f"💾 Saving to cache at: {parquet_path}")
    df.to_parquet(parquet_path, index=False)
    return df


def check_if_all_solutions_are_feasible(solutions_df: pd.DataFrame, tolerance: float = 1e-2) -> None:
    """
    Verifies that in every solution, the last arrival time in the congested schedule for each trip
    does not exceed its deadline by more than a small tolerance. Prints details about infeasible rows.
    """

    def is_feasible(row, idx) -> bool:
        try:
            schedules = row["solution_congested_schedule"]
            deadlines = row["instance_deadlines"]

            # Accept both list and ndarray
            if not isinstance(schedules, (list, np.ndarray)) or not isinstance(deadlines, (list, np.ndarray)):
                print(f"⚠️ Row {idx}: Expected list or ndarray types, got {type(schedules)} and {type(deadlines)}")
                return False

            if len(schedules) != len(deadlines):
                print(f"⚠️ Row {idx}: Length mismatch: {len(schedules)} schedules vs {len(deadlines)} deadlines")
                return False

            for i, (schedule, deadline) in enumerate(zip(schedules, deadlines)):
                if not isinstance(schedule, (list, np.ndarray)) or len(schedule) == 0:
                    print(f"⚠️ Row {idx}, trip {i}: Invalid or empty schedule: {schedule}")
                    return False
                last_arrival = schedule[-1]
                if last_arrival > deadline + tolerance:
                    print(
                        f"❌ Row {idx}, trip {i}: Arrival {last_arrival:.2f} > Deadline {deadline:.2f} + tol {tolerance:.2f} "
                        f"(Exceeded by {last_arrival - deadline:.2f})"
                    )
                    return False

            return True

        except Exception as e:
            print(f"⚠️ Row {idx}: Error checking feasibility: {e}")
            return False

    infeasible_rows = []
    for idx, row in solutions_df.iterrows():
        if not is_feasible(row, idx):
            infeasible_rows.append(idx)

    if infeasible_rows:
        print(f"\n❌ Found {len(infeasible_rows)} infeasible solution(s): Rows {infeasible_rows}")
    else:
        print("✅ All solutions are feasible within the allowed tolerance.")


def add_additional_columns_to_df(solutions_df: pd.DataFrame,
                                 solutions_computed: bool = True) -> pd.DataFrame:
    """
    Adds derived columns to the DataFrame for total delays in hours and delay reductions.
    Assumes delays are in seconds.
    """
    # Status quo metrics
    solutions_df["status_quo_total_delay_hours"] = solutions_df["status_quo_total_delay"] / 3600
    solutions_df["status_quo_delays_on_arcs_minutes"] = solutions_df["status_quo_delays_on_arcs"].apply(
        lambda nested: [[val / 60.0 for val in sublist] for sublist in nested]
    )
    solutions_df["status_quo_total_delay_trips_minutes"] = solutions_df["status_quo_delays_on_arcs_minutes"].apply(
        lambda nested: [sum(sublist) for sublist in nested]
    )

    if solutions_computed:
        # Solution metrics
        solutions_df["solution_total_delay_hours"] = solutions_df["solution_total_delay"] / 3600

        # Compute reductions
        solutions_df["absolute_delay_reduction_hours"] = (
                solutions_df["status_quo_total_delay_hours"] - solutions_df["solution_total_delay_hours"]
        )
        solutions_df["relative_delay_reduction"] = (solutions_df["absolute_delay_reduction_hours"] /
                                                    solutions_df["status_quo_total_delay_hours"]) * 100

    return solutions_df


def plot_delay_reductions(solutions_df: pd.DataFrame, path_to_figures: Path):
    """
    Plots absolute and relative delay reductions grouped by flow constraints.

    Args:
        solutions_df (pd.DataFrame): DataFrame containing computed delay reductions.
        path_to_figures (Path): Path to save the figures.
    """
    sns.set(style="whitegrid", font_scale=1.2)
    path_to_figures.mkdir(parents=True, exist_ok=True)

    # Label flow levels for readability
    min_flow = solutions_df["instance_parameters_max_flow_allowed"].min()
    max_flow = solutions_df["instance_parameters_max_flow_allowed"].max()

    def label_flow(val):
        if val == min_flow:
            return "LC"
        elif val == max_flow:
            return "HC"
        return str(val)

    solutions_df["Flow Level"] = solutions_df["instance_parameters_max_flow_allowed"].apply(label_flow)

    # --- Absolute delay reduction plot ---
    plt.figure(figsize=(8, 5))
    sns.boxplot(
        data=solutions_df,
        x="absolute_delay_reduction_hours",
        hue="Flow Level",
        legend=False,
        palette="Blues",
        orient="h",
    )
    plt.xlabel("Absolute Delay Reduction (hours)")
    plt.ylabel("Max Flow Constraint")
    plt.title("Absolute Delay Reduction by Flow Level")
    plt.tight_layout()
    plt.savefig(path_to_figures / "absolute_delay_reduction_hours.png")
    plt.close()

    # --- Relative delay reduction plot ---
    plt.figure(figsize=(8, 5))
    sns.boxplot(
        data=solutions_df,
        x="relative_delay_reduction",
        hue="Flow Level",
        legend=False,
        palette="Greens",
        orient="h",
    )
    plt.xlabel("Relative Delay Reduction")
    plt.ylabel("Max Flow Constraint")
    plt.title("Relative Delay Reduction by Flow Level")
    plt.tight_layout()
    plt.savefig(path_to_figures / "relative_delay_reduction_percentage.png")
    plt.close()

    print(f"✅ Figures saved to {path_to_figures}")
