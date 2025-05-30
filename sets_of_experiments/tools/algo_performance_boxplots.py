import os
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import seaborn as sns
import tikzplotlib
import warnings
from matplotlib import MatplotlibDeprecationWarning
import numpy as np

# Suppress specific MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def get_algo_performance_boxplots(results_df: pd.DataFrame, path_to_figures: Path, verbose: bool = False) -> None:
    """
    Generate and save boxplots for algorithm performance metrics as JPEG and TeX files,
    creating separate figures for LC and HC experiments. When verbose is True, print the
    values being plotted for each experiment.
    """
    print("\n" + "=" * 50)
    print("Starting get_algo_performance_boxplots function".center(50))
    print("=" * 50 + "\n")

    # Calculate absolute and relative delay reduction
    print("Step 1: Calculating delay reductions...")
    results_df['absolute_delay_reduction_seconds'] = results_df['status_quo_total_delay'] - results_df[
        'solution_total_delay']
    results_df['absolute_delay_reduction_minutes'] = results_df[
                                                         'absolute_delay_reduction_seconds'] / 60  # Convert to minutes
    results_df['absolute_delay_reduction_hrs'] = results_df[
                                                     'absolute_delay_reduction_minutes'] / 60  # Convert to minutes
    results_df['relative_delay_reduction'] = (
            results_df['absolute_delay_reduction_seconds'] / results_df['status_quo_total_delay'] * 100
    )
    print("Delay reductions calculated (absolute in minutes, relative in percentage).")

    # Add a label for solver_parameters_epoch_size
    print("\nStep 2: Adding labels for solver parameters...")
    results_df['epoch_label'] = results_df['solver_parameters_epoch_size'].apply(
        lambda x: "OFF" if x == 60 else "ON"
    )
    print("Labels added.")

    # Separate data by congestion level
    print("\nStep 3: Splitting data by congestion level...")
    lc_data = results_df[results_df['congestion_level'] == "LC"]
    hc_data = results_df[results_df['congestion_level'] == "HC"]

    def plot_boxplot(data, x_col, y_col, ylabel, xlabel, file_name, label, is_percentage=False, x_limits=None):
        print(f"\nCreating boxplot for {file_name}...")

        if verbose:
            # Print values being plotted in a tidy format
            print(f"\nValues for {label} - {x_col}:")
            for epoch_label in data[y_col].unique():
                filtered_data = data[data[y_col] == epoch_label][x_col].dropna().round(2).tolist()
                print(f"  {epoch_label}: {filtered_data}")

        # Set the desired figure dimensions
        marker_size = 4  # Size of markers
        box_width = 0.85  # Width of boxplots

        plt.figure(figsize=(6.5, 4.0))  # Use standard figure size for consistency

        # Create the boxplot with customized box width
        sns.boxplot(
            x=x_col,
            y=y_col,
            data=data,
            width=box_width,
            boxprops=dict(facecolor='white', edgecolor='black'),
            flierprops=dict(marker='o', markerfacecolor='white', markeredgecolor='black', markersize=marker_size),
            medianprops=dict(color='black'),
            whiskerprops=dict(color='black'),
            capprops=dict(color='black')
        )

        # Add scatter points with customized marker size
        sns.stripplot(
            x=x_col,
            y=y_col,
            data=data,
            color="white",  # Use a valid color
            edgecolor="black",  # Black outline for the points
            size=marker_size,
            jitter=True,
            linewidth=1
        )

        # Add vertical grid lines
        plt.grid(axis='x', linestyle='--', color='gray', alpha=0.7)

        # Customize labels
        plt.ylabel(ylabel)
        plt.xlabel(xlabel)

        # Set x-axis limits if specified
        if x_limits is not None:
            plt.xlim(x_limits)

        # Set x-axis ticks and limits for percentage plots
        if is_percentage:
            plt.xticks(ticks=np.arange(0, 101, 20), labels=np.arange(0, 101, 20))
            plt.xlim(-1, 101)  # Ensure x-axis starts at 0 and ends at 100

        plt.tight_layout()

        # Save the figure as a JPEG
        os.makedirs(path_to_figures / "performance_boxplots", exist_ok=True)
        plt.savefig(path_to_figures / "performance_boxplots" / f"{file_name}.jpeg", format="jpeg", dpi=300)

        # Save the figure as TeX, with custom placeholders for width and height
        tikzplotlib.save(
            str(path_to_figures / "performance_boxplots" / f"{file_name}.tex"),
            axis_width=r"\DelayReductionWidth",
            axis_height=r"\DelayReductionHeight"
        )

        plt.close()
        print(f"Boxplot for {file_name} saved.")

    # Generate plots for LC experiments
    # Determine global x-axis limits for absolute delay reduction
    global_min = min(lc_data['absolute_delay_reduction_hrs'].min(),
                     hc_data['absolute_delay_reduction_hrs'].min())
    global_max = max(lc_data['absolute_delay_reduction_hrs'].max(),
                     hc_data['absolute_delay_reduction_hrs'].max())
    x_limits_absolute = (global_min - 1, global_max + 1)
    print("\nStep 4: Generating plots for LC experiments...")
    # Generate plots for LC experiments with fixed x-axis
    plot_boxplot(
        data=lc_data,
        x_col='absolute_delay_reduction_hrs',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [hrs]",  # Updated unit to minutes
        file_name="absolute_delay_reduction_LC",
        label="LC",
    )

    plot_boxplot(
        data=lc_data,
        x_col='relative_delay_reduction',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [\%]",
        file_name="relative_delay_reduction_LC",
        label="LC",
        is_percentage=True
    )

    # Generate plots for HC experiments
    print("\nStep 5: Generating plots for HC experiments...")
    # Generate plots for HC experiments with fixed x-axis
    plot_boxplot(
        data=hc_data,
        x_col='absolute_delay_reduction_hrs',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [hrs]",  # Updated unit to minutes
        file_name="absolute_delay_reduction_HC",
        label="HC",
    )
    plot_boxplot(
        data=hc_data,
        x_col='relative_delay_reduction',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [\%]",
        file_name="relative_delay_reduction_HC",
        label="HC",
        is_percentage=True
    )

    print("\n" + "=" * 50)
    print("Completed get_algo_performance_boxplots function".center(50))
    print("=" * 50 + "\n")
