import os

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import seaborn as sns
import tikzplotlib
import warnings
from matplotlib import MatplotlibDeprecationWarning

# Suppress specific MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def get_algo_performance_boxplots(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save boxplots for algorithm performance metrics as JPEG and TeX files.
    """
    print("\n" + "=" * 50)
    print("Starting get_algo_performance_boxplots function".center(50))
    print("=" * 50 + "\n")

    # Calculate absolute and relative delay reduction
    print("Step 1: Calculating delay reductions...")
    results_df['absolute_delay_reduction'] = results_df['status_quo_total_delay'] - results_df['solution_total_delay']
    results_df['relative_delay_reduction'] = (
            results_df['absolute_delay_reduction'] / results_df['status_quo_total_delay'] * 100
    )
    print("Delay reductions calculated.")

    # Add a label for solver_parameters_epoch_size
    print("\nStep 2: Adding labels for solver parameters...")
    results_df['epoch_label'] = results_df['solver_parameters_epoch_size'].apply(
        lambda x: "OFF" if x == 60 else "ON"
    )
    print("Labels added.")

    def plot_boxplot(data, x_col, y_col, ylabel, xlabel, file_name):
        print(f"\nCreating boxplot for {file_name}...")
        # Set the desired figure dimensions
        marker_size = 4  # Size of markers
        box_width = 0.8  # Width of boxplots

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

        # Customize labels and save the plot
        plt.ylabel(ylabel)
        plt.xlabel(xlabel)
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

    # First figure: absolute delay reduction in seconds
    print("\nStep 3: Generating plots...")
    plot_boxplot(
        data=results_df,
        x_col='absolute_delay_reduction',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [sec]",
        file_name="absolute_delay_reduction"
    )

    # Second figure: relative delay reduction in percentage
    plot_boxplot(
        data=results_df,
        x_col='relative_delay_reduction',
        y_col='epoch_label',
        ylabel="",
        xlabel=r"$\Theta$ [\%]",
        file_name="relative_delay_reduction"
    )

    print("\n" + "=" * 50)
    print("Completed get_algo_performance_boxplots function".center(50))
    print("=" * 50 + "\n")