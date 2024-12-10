import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path


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

    # Calculate bounds difference
    print("=" * 50)
    print("Step 4: Calculating bounds difference".center(50))
    print("=" * 50 + "\n")
    filtered_df['optimization_measures_bounds_difference_final'] = (
            filtered_df['optimization_measures_upper_bound_final'] -
            filtered_df['optimization_measures_lower_bound_final']
    )
    print("Bounds difference calculated.\n")

    # Split the data into LC and HC
    print("=" * 50)
    print("Step 5: Splitting data by congestion level".center(50))
    print("=" * 50 + "\n")
    lc_data = filtered_df[filtered_df['congestion_level'] == "LC"]
    hc_data = filtered_df[filtered_df['congestion_level'] == "HC"]

    def plot_horizontal_boxplot(data, x_col, xlabel, file_name, label):
        """Helper function to create horizontal boxplots."""
        print(f"Creating boxplot for '{file_name}'...")

        if verbose:
            # Print all values in a single line for the current plot
            values = data[x_col].dropna().tolist()
            print(f"\nValues for {label} - {x_col}: {values}")

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
        x_col='optimization_measures_optimality_gap_final',
        xlabel=r"$\Delta$ [\%] (LC)",
        file_name="optimality_gap_LC",
        label="LC"
    )
    plot_horizontal_boxplot(
        data=lc_data,
        x_col='optimization_measures_lower_bound_final',
        xlabel="LB [sec] (LC)",
        file_name="lower_bound_LC",
        label="LC"
    )
    plot_horizontal_boxplot(
        data=lc_data,
        x_col='optimization_measures_bounds_difference_final',
        xlabel=r"$\Delta$ [sec] (LC)",
        file_name="bounds_difference_LC",
        label="LC"
    )

    # Generate boxplots for HC experiments
    print("\nGenerating boxplots for HC experiments...")
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_optimality_gap_final',
        xlabel=r"$\Delta$ [\%] (HC)",
        file_name="optimality_gap_HC",
        label="HC"
    )
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_lower_bound_final',
        xlabel="LB [sec] (HC)",
        file_name="lower_bound_HC",
        label="HC"
    )
    plot_horizontal_boxplot(
        data=hc_data,
        x_col='optimization_measures_bounds_difference_final',
        xlabel=r"$\Delta$ [sec] (HC)",
        file_name="bounds_difference_HC",
        label="HC"
    )

    print("\n" + "=" * 50)
    print("Completed get_mip_bounds_boxplots function".center(50))
    print("=" * 50 + "\n")
