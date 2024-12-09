import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path


def get_mip_bounds_boxplots(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save horizontal boxplots for MIP bounds metrics.
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
    # Extract the first dictionary from the list
    filtered_df['optimization_measures'] = filtered_df['optimization_measures_list'].apply(
        lambda x: x[0] if x else {}
    )
    print("Extracting and flattening dictionaries into columns...")
    # Flatten the dictionaries into separate columns
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

    # Calculate bounds difference
    print("=" * 50)
    print("Step 4: Calculating bounds difference".center(50))
    print("=" * 50 + "\n")
    filtered_df['optimization_measures_bounds_difference_final'] = (
            filtered_df['optimization_measures_upper_bound_final'] -
            filtered_df['optimization_measures_lower_bound_final']
    )
    print("Bounds difference calculated.\n")

    # Step 5: Generate boxplots
    print("=" * 50)
    print("Step 5: Generating boxplots".center(50))
    print("=" * 50 + "\n")

    def plot_horizontal_boxplot(data, x_col, xlabel, file_name):
        """Helper function to create horizontal boxplots."""
        print(f"Creating boxplot for '{file_name}'...")
        plt.figure(figsize=(6.5, 4.0))  # Standard figure size

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
        plt.tight_layout()

        # Save the figure
        output_dir = path_to_figures / "mip_bounds_boxplots"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)

        # Save TeX representation
        tikzplotlib.save(
            str(output_dir / f"{file_name}.tex"),
            axis_width=r"\MipBoundsWidth",
            axis_height=r"\MipBoundsHeight"
        )

        plt.close()
        print(f"Boxplot for '{file_name}' saved.\n")

    # Generate plots for required metrics
    plot_horizontal_boxplot(
        data=filtered_df,
        x_col='optimization_measures_optimality_gap_final',
        xlabel=r"$\Delta$ [\%]",
        file_name="optimality_gap"
    )

    plot_horizontal_boxplot(
        data=filtered_df,
        x_col='optimization_measures_lower_bound_final',
        xlabel="LB [sec]",  # Using plain text to avoid mathtext parsing issues
        file_name="lower_bound"
    )

    plot_horizontal_boxplot(
        data=filtered_df,
        x_col='optimization_measures_bounds_difference_final',
        xlabel=r"$\Delta$ [sec]",
        file_name="bounds_difference"
    )

    print("\n" + "=" * 50)
    print("Completed get_mip_bounds_boxplots function".center(50))
    print("=" * 50 + "\n")
