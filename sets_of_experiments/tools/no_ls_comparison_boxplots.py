import os

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import seaborn as sns
import tikzplotlib
import warnings
from matplotlib import MatplotlibDeprecationWarning
import matplotlib as mpl

mpl.rcParams['text.usetex'] = True

mpl.rcParams.update(mpl.rcParamsDefault)
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def get_no_ls_comparison_boxplot(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save boxplots for solution total delay and improvements (absolute/percentage),
    grouped by solver_parameters_improve_warm_start (MILP/MATH), with the x-axis representing delay or improvement.
    """
    print("\nStarting get_no_ls_comparison_boxplot function")

    # Compute derived columns
    print("Preparing data with derived metrics...")
    results_df["solution_total_delay_minutes"] = results_df["solution_total_delay"] / 60
    results_df["status_quo_total_delay_minutes"] = results_df["status_quo_total_delay"] / 60
    results_df["absolute_improvement_minutes"] = (
            results_df["status_quo_total_delay_minutes"] - results_df["solution_total_delay_minutes"]
    )
    results_df["percentage_improvement"] = (
                                                   results_df["absolute_improvement_minutes"] / results_df[
                                               "status_quo_total_delay_minutes"]
                                           ) * 100

    # Map True/False to labels
    results_df["solver_label"] = results_df["solver_parameters_improve_warm_start"].map(
        {True: r"\texttt{MATH}", False: r"\texttt{MILP}"}
    )

    # Split data by congestion levels
    print("Splitting data by congestion levels...")
    lc_data = results_df[results_df['congestion_level'] == "LC"]
    hc_data = results_df[results_df['congestion_level'] == "HC"]

    # Helper function to create and save boxplots
    def plot_no_ls_boxplot(data, x_col, xlabel, folder_name, file_name):
        print(f"Creating boxplot for {file_name}...")

        # Create a new figure with a fixed size
        plt.figure(figsize=(6.5, 4.0))

        # Create the boxplot
        sns.boxplot(
            x=x_col,
            y="solver_label",
            data=data,
            orient="h",  # Horizontal orientation
            width=0.7,
            boxprops=dict(facecolor='white', edgecolor='black'),
            flierprops=dict(marker='o', markerfacecolor='white', markeredgecolor='black', markersize=4),
            medianprops=dict(color='black'),
            whiskerprops=dict(color='black'),
            capprops=dict(color='black')
        )

        # Customize labels
        plt.xlabel(xlabel)
        plt.ylabel(" ")

        # Add gridlines
        plt.grid(axis='x', linestyle='--', color='gray', alpha=0.7)

        # Adjust layout
        plt.tight_layout()

        # Ensure output directory exists
        output_dir = path_to_figures / folder_name
        os.makedirs(output_dir, exist_ok=True)

        # Save the figure as JPEG
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300, bbox_inches="tight")

        # Save the figure as TeX
        tikzplotlib.save(
            str(output_dir / f"{file_name}.tex"),
            axis_width=r"\PWLWidth",
            axis_height=r"\PWLHeight"
        )

        plt.close()
        print(f"Boxplot for {file_name} saved.")

    # Define boxplots for each metric
    metrics = [
        ("solution_total_delay_minutes", "Solution Total Delay [min]",
         "solution_delay"),
        ("absolute_improvement_minutes", r"\$\DelayReduction\$[min]",
         "absolute_improvement"),
        ("percentage_improvement", r"\$\DelayReduction\$[%]",
         "percentage_improvement")
    ]

    # Generate boxplots for each congestion level and metric
    for x_col, xlabel, metric_name in metrics:
        print(f"Generating plots for LC data ({metric_name})...")
        plot_no_ls_boxplot(
            data=lc_data,
            x_col=x_col,
            xlabel=xlabel,
            folder_name=f"no_ls_boxplots/{metric_name}_LC",
            file_name=f"no_ls_boxplot_{metric_name}_LC"
        )

        print(f"Generating plots for HC data ({metric_name})...")
        plot_no_ls_boxplot(
            data=hc_data,
            x_col=x_col,
            xlabel=xlabel,
            folder_name=f"no_ls_boxplots/{metric_name}_HC",
            file_name=f"no_ls_boxplot_{metric_name}_HC"
        )

    print("Completed get_no_ls_comparison_boxplot function")
