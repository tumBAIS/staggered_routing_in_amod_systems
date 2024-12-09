import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
from matplotlib import MatplotlibDeprecationWarning

# Suppress specific MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def get_staggering_analysis_plots(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save plots for staggering analysis:
    1. Bar plot: x-axis is `instance_parameters_staggering_cap`, y-axis is `solution_total_delay`.
    2. Vertical boxplots: x-axis is `instance_parameters_staggering_cap`, y-axis is `solution_staggering_applied`.
    """
    print("\n" + "=" * 50)
    print("Starting get_staggering_analysis_plots".center(50))
    print("=" * 50 + "\n")

    # Step 1: Create the bar plot
    print("Creating bar plot...".center(50))
    plt.figure(figsize=(6.5, 4.0))
    sns.barplot(
        x="instance_parameters_staggering_cap",
        y="solution_total_delay",
        data=results_df,
        color="gray",
        edgecolor="black"
    )
    plt.xlabel(r"$\zeta^{\mathrm{MAX}}$ [%]")
    plt.ylabel(r"$Z(\pi)$ [min]")
    plt.grid(axis='y', linestyle='--', color='gray', alpha=0.7)
    plt.tight_layout()

    # Save bar plot
    output_dir = path_to_figures / "staggering_analysis_plots"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_dir / "staggering_total_delay_barplot.jpeg", format="jpeg", dpi=300)
    plt.close()
    print("Bar plot saved.".center(50))

    # Step 2: Create the vertical boxplots
    print("Creating vertical boxplots...".center(50))
    plt.figure(figsize=(6.5, 4.0))
    # Explode the lists in `solution_staggering_applied` for boxplot generation
    exploded_df = results_df.explode("solution_staggering_applied").dropna(subset=["solution_staggering_applied"])

    sns.boxplot(
        x="instance_parameters_staggering_cap",
        y="solution_staggering_applied",
        data=exploded_df,
        width=0.8,
        boxprops=dict(facecolor='white', edgecolor='black'),
        flierprops=dict(marker='x', color='black'),
        medianprops=dict(color='black'),
        whiskerprops=dict(color='black'),
        capprops=dict(color='black')
    )
    plt.xlabel(r"$\zeta^{\mathrm{MAX}}$ [%]")
    plt.ylabel(r"$\sigma^\pi$ [min]")
    plt.grid(axis='y', linestyle='--', color='gray', alpha=0.7)
    plt.tight_layout()

    # Save boxplots
    plt.savefig(output_dir / "staggering_applied_boxplot.jpeg", format="jpeg", dpi=300)
    plt.close()
    print("Boxplots saved.".center(50))

    print("\n" + "=" * 50)
    print("Completed get_staggering_analysis_plots".center(50))
    print("=" * 50 + "\n")
