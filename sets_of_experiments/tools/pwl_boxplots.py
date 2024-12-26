import os

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import seaborn as sns
import tikzplotlib
import matplotlib as mpl
import warnings
from matplotlib import MatplotlibDeprecationWarning

mpl.rcParams.update(mpl.rcParamsDefault)
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def get_pwl_boxplots(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save boxplots for piecewise linear parameters (slopes and thresholds)
    based on congestion levels (LC and HC).
    """
    print("\nStarting get_pwl_boxplots function")
    print("Creating combined label column...")

    results_df['combination_label'] = results_df['instance_parameters_list_of_slopes'].astype(str) + " | " + results_df[
        'instance_parameters_list_of_thresholds'].astype(str)

    # Adding necessary columns

    results_df["status_quo_total_delay_minutes"] = results_df["status_quo_total_delay"] / 60
    results_df["solution_total_delay_minutes"] = results_df["solution_total_delay"] / 60

    results_df["absolute_delay_reduction_minutes"] = (results_df["status_quo_total_delay_minutes"] -
                                                      results_df["solution_total_delay_minutes"])

    results_df["relative_delay_reduction"] = (results_df["status_quo_total_delay_minutes"] -
                                              results_df["solution_total_delay_minutes"]) / results_df[
                                                 "status_quo_total_delay_minutes"] * 100

    # Split the data based on congestion levels
    print("Splitting data by congestion levels...")
    lc_data = results_df[results_df['congestion_level'] == "LC"]
    hc_data = results_df[results_df['congestion_level'] == "HC"]

    # Helper function to create and save boxplots
    def plot_pwl_boxplot(data, x_col, y_col, xlabel, folder_name, file_name, x_limits=None):
        print(f"Creating boxplot for {file_name}...")

        # Create a new figure with a fixed size
        plt.figure(figsize=(6.5, 4.0))

        # Create the boxplot
        sns.boxplot(
            x=x_col,
            y=y_col,
            data=data,
            width=0.85,
            boxprops=dict(facecolor='white', edgecolor='black'),
            flierprops=dict(marker='o', markerfacecolor='white', markeredgecolor='black', markersize=4),
            medianprops=dict(color='black'),
            whiskerprops=dict(color='black'),
            capprops=dict(color='black')
        )

        # Add scatter points with fixed jitter for reproducibility
        sns.stripplot(
            x=x_col,
            y=y_col,
            data=data,
            color="white",
            edgecolor="black",
            size=4,
            jitter=0.2,  # Fixed jitter value
            linewidth=1
        )

        # Customize labels
        plt.xlabel(xlabel)
        plt.ylabel("")  # Remove ylabel

        # Customize y-axis ticks to display PWL n
        y_ticks = [f"PWL {i + 1}" for i in range(len(data[y_col].unique()))]
        plt.yticks(ticks=range(len(data[y_col].unique())), labels=y_ticks)

        # Set x-axis limits if provided
        if x_limits is not None:
            plt.xlim(x_limits)

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

    # Define the columns and folder names for the plots
    plot_configs = [
        ("status_quo_total_delay_minutes", "[min]", "delay_minutes", None),
        ("absolute_delay_reduction_minutes", "[min]", "absolute_reduction", None),
        ("relative_delay_reduction", "[%]", "relative_reduction", (0, 100))
    ]

    # Generate plots for each metric and congestion level
    for x_col, xlabel, folder_name, x_limits in plot_configs:
        print(f"Generating plots for LC data ({folder_name})...")
        plot_pwl_boxplot(
            data=lc_data,
            x_col=x_col,
            y_col='combination_label',
            xlabel=xlabel,
            folder_name=f"pwl_boxplots/{folder_name}_LC",
            file_name=f"pwl_boxplot_{folder_name}_LC",
            x_limits=x_limits
        )

        print(f"Generating plots for HC data ({folder_name})...")
        plot_pwl_boxplot(
            data=hc_data,
            x_col=x_col,
            y_col='combination_label',
            xlabel=xlabel,
            folder_name=f"pwl_boxplots/{folder_name}_HC",
            file_name=f"pwl_boxplot_{folder_name}_HC",
            x_limits=x_limits
        )

    print("Completed get_pwl_boxplots function")
