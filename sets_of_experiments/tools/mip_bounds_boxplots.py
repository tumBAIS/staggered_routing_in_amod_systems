import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path
import numpy as np


def get_mip_bounds_boxplots(results_df: pd.DataFrame, path_to_figures: Path, verbose: bool = False) -> None:
    """
    Generate and save horizontal boxplots for MIP bounds metrics, separately for LC and HC experiments.
    If verbose is True, print the values of the points being plotted for each experiment on the same line.
    """
    print("\n" + "=" * 50)
    print("Starting get_mip_bounds_boxplots function".center(50))
    print("=" * 50 + "\n")

    # Step 1: Filter the DataFrame for `solver_parameters_epoch_size == 60`
    print("Step 1: Filtering the DataFrame for 'solver_parameters_epoch_size == 60'...")
    filtered_df = results_df[results_df['solver_parameters_epoch_size'] == 60].copy()
    print(f"Filtered DataFrame contains {len(filtered_df)} rows.\n")

    # Step 2: Process the `optimization_measures_list` column
    print("=" * 50)
    print("Step 2: Processing 'optimization_measures_list' column".center(50))
    print("=" * 50 + "\n")

    filtered_df['optimization_measures'] = filtered_df['optimization_measures_list'].apply(
        lambda x: x[0] if x else {}
    )
    measures_df = filtered_df['optimization_measures'].apply(pd.Series)
    measures_df = measures_df.add_prefix('optimization_measures_')
    filtered_df = pd.concat([filtered_df, measures_df], axis=1)
    print("Flattened dictionaries successfully.\n")

    # Extract final values from columns ending with `_list`
    print("=" * 50)
    print("Step 3: Extracting final values from '_list' columns".center(50))
    print("=" * 50 + "\n")
    list_columns = [col for col in filtered_df.columns if col.endswith('_list')]
    for col in list_columns:
        final_col = col.replace('_list', '_final')
        filtered_df[final_col] = filtered_df[col].apply(lambda x: x[-1] if isinstance(x, list) and x else None)
    print("Final values extracted from list columns.\n")

    # Calculate bounds difference and convert time values to minutes
    print("=" * 50)
    print("Step 4: Calculating bounds difference and converting time to minutes".center(50))
    print("=" * 50 + "\n")

    nan_rows = filtered_df[
        filtered_df[['optimization_measures_upper_bounds_final',
                     'optimization_measures_lower_bounds_final',
                     'optimization_measures_optimality_gaps_final']].isna().any(axis=1)
    ]

    if not nan_rows.empty:
        print(f"Found {len(nan_rows)} rows with NaN values. Replacing with default values...")
        filtered_df = filtered_df.copy()  # Ensure a deep copy to avoid chained assignment warnings
        filtered_df['optimization_measures_upper_bounds_final'] = filtered_df[
            'optimization_measures_upper_bounds_final'].fillna(
            filtered_df['solution_total_delay']
        )
        filtered_df['optimization_measures_lower_bounds_final'] = filtered_df[
            'optimization_measures_lower_bounds_final'].fillna(0)
        filtered_df['optimization_measures_optimality_gaps_final'] = filtered_df[
            'optimization_measures_optimality_gaps_final'].fillna(100)
        print("NaN values replaced.\n")

    filtered_df['optimization_measures_bounds_difference_final'] = (
            filtered_df['optimization_measures_upper_bounds_final'] -
            filtered_df['optimization_measures_lower_bounds_final']
    )
    filtered_df['optimization_measures_lower_bounds_final'] /= 60  # Convert to minutes
    filtered_df['optimization_measures_bounds_difference_final'] /= 60  # Convert to minutes

    print("Bounds difference calculated and time values converted to minutes.\n")

    # Split the data into LC and HC
    print("=" * 50)
    print("Step 5: Splitting data by congestion level".center(50))
    print("=" * 50 + "\n")
    lc_data = filtered_df[filtered_df['congestion_level'] == "LC"]
    hc_data = filtered_df[filtered_df['congestion_level'] == "HC"]

    def plot_horizontal_boxplot(data, x_col, xlabel, file_name, label, is_percentage=False, xlimits=None):
        """Helper function to create horizontal boxplots."""
        print(f"Creating boxplot for '{file_name}'...")

        if verbose:
            # Print all values in a single line for the current plot
            values = data[x_col].dropna().round(2).tolist()
            print(f"\nValues for {label} - {x_col}:\n {values}")

        plt.figure(figsize=(6.5, 4.0))

        sns.boxplot(
            x=x_col,
            data=data,
            orient='h',
            width=0.8,
            boxprops=dict(facecolor='white', edgecolor='black'),
            flierprops=dict(marker='o', markerfacecolor='white', markeredgecolor='black', markersize=4),
            medianprops=dict(color='black'),
            whiskerprops=dict(color='black'),
            capprops=dict(color='black')
        )

        sns.stripplot(
            x=x_col,
            data=data,
            color="white",
            edgecolor="black",
            size=4,
            jitter=True,
            linewidth=1
        )

        plt.grid(axis='x', linestyle='--', color='gray', alpha=0.7)
        plt.xlabel(xlabel)

        # Set x-axis limits for percentage boxplots
        if is_percentage:
            plt.xlim(-1, 101)  # Set limits for percentage boxplots
            plt.xticks(ticks=np.arange(0, 101, 20), labels=np.arange(0, 101, 20))
        elif xlimits:
            plt.xlim(xlimits[0], xlimits[1])  # Set custom x-axis limits for time values
            # plt.xticks(ticks=np.arange(xlimits[0] + 1, xlimits[1]))

        plt.tight_layout()

        output_dir = path_to_figures / "mip_bounds_boxplots"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)

        tikzplotlib.save(
            str(output_dir / f"{file_name}.tex"),
            axis_width=r"\MipBoundsWidth",
            axis_height=r"\MipBoundsHeight"
        )

        plt.close()
        print(f"Boxplot for '{file_name}' saved.\n")

    # Generate boxplots for LC experiments
    print("\nGenerating boxplots for LC experiments...")
    plot_horizontal_boxplot(
        data=lc_data,
        x_col='optimization_measures_optimality_gaps_final',
        xlabel=r"$\Delta$ [\%] (LC)",
        file_name="optimality_gap_LC",
        label="LC",
        is_percentage=True,
        xlimits=(-1, None)
    )
    plot_horizontal_boxplot(
        data=lc_data,
        x_col='optimization_measures_lower_bounds_final',
        xlabel="LB [min] (LC)",  # Adjusted to minutes
        file_name="lower_bound_LC",
        label="LC",
        xlimits=(-1, 11)  # Adjust xlimits for time values if needed
    )
    plot_horizontal_boxplot(
        data=lc_data,
        x_col='optimization_measures_bounds_difference_final',
        xlabel=r"$\Delta$ [min] (LC)",  # Adjusted to minutes
        file_name="bounds_difference_LC",
        label="LC",
        xlimits=(-.99, None)  # Adjust xlimits for time values if needed
    )

    # Generate boxplots for HC experiments
    print("\nGenerating boxplots for HC experiments...")
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_optimality_gaps_final',
        xlabel=r"$\Delta$ [\%] (HC)",
        file_name="optimality_gap_HC",
        label="HC",
        is_percentage=True,
        xlimits=(-1, None)
    )
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_lower_bounds_final',
        xlabel="LB [min] (HC)",  # Adjusted to minutes
        file_name="lower_bound_HC",
        label="HC",
        xlimits=(-1, None)  # Adjust xlimits for time values if needed
    )
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_bounds_difference_final',
        xlabel=r"$\Delta$ [min] (HC)",  # Adjusted to minutes
        file_name="bounds_difference_HC",
        label="HC",
        xlimits=(-1, None)  # Adjust xlimits for time values if needed
    )

    print("\n" + "=" * 50)
    print("Completed get_mip_bounds_boxplots function".center(50))
    print("=" * 50 + "\n")
