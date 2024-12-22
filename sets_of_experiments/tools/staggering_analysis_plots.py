import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
from matplotlib import MatplotlibDeprecationWarning
import tikzplotlib

# Suppress specific MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def get_staggering_analysis_plots(results_df: pd.DataFrame, path_to_figures: Path) -> None:
    """
    Generate and save plots for staggering analysis:
    1. Bar plot: x-axis is `instance_parameters_staggering_cap`, y-axis is `solution_total_delay`.
    2. Vertical boxplots: x-axis is `instance_parameters_staggering_cap`, y-axis is `solution_staggering_applied`.
    Separate plots are generated for LC and HC congestion levels. Figures are saved as both JPEG and TeX files.
    """
    print("\n" + "=" * 50)
    print("Starting get_staggering_analysis_plots".center(50))
    print("=" * 50 + "\n")

    # Step 1: Split the data into LC and HC
    print("Splitting data into LC and HC...".center(50))
    lc_data = results_df[results_df["congestion_level"] == "LC"].copy()
    hc_data = results_df[results_df["congestion_level"] == "HC"].copy()
    print(f"LC data contains {len(lc_data)} rows.".center(50))
    print(f"HC data contains {len(hc_data)} rows.".center(50))

    # Convert solution_total_delay and solution_staggering_applied to minutes
    for data in [lc_data, hc_data]:
        data.loc[:, "solution_total_delay"] = data["solution_total_delay"] / 60  # Convert to minutes
        data.loc[:, "solution_staggering_applied"] = data["solution_staggering_applied"].apply(
            lambda x: [v / 60 for v in x] if isinstance(x, list) else x  # Convert lists to minutes
        )

        # # Process solution_total_delay to ensure non-decreasing order
        # data.sort_values("instance_parameters_staggering_cap", inplace=True)
        # for i in range(1, len(data)):
        #     if data.iloc[i]["solution_total_delay"] > data.iloc[i - 1]["solution_total_delay"]:
        #         data.iloc[i, data.columns.get_loc("solution_total_delay")] = data.iloc[i - 1]["solution_total_delay"]

    # Step 2: Define a helper function for generating the plots
    def generate_plots(data, label):
        print(f"\nGenerating plots for {label}...".center(50))

        # Bar plot
        print(f"Creating bar plot for {label}...".center(50))
        plt.figure(figsize=(6.5, 4.0))
        sns.barplot(
            x="instance_parameters_staggering_cap",
            y="solution_total_delay",
            data=data,
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
        file_name = f"staggering_total_delay_barplot_{label.lower()}"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)
        tikzplotlib.save(output_dir / f"{file_name}.tex")
        plt.close()
        print(f"Bar plot for {label} saved.".center(50))

        # Boxplot
        print(f"Creating boxplot for {label}...".center(50))
        plt.figure(figsize=(6.5, 4.0))
        # Explode the lists in `solution_staggering_applied` for boxplot generation
        exploded_data = data.explode("solution_staggering_applied").dropna(subset=["solution_staggering_applied"])
        exploded_data = exploded_data[exploded_data["solution_staggering_applied"] > 1e-4]
        null_pont = pd.DataFrame({
            "instance_parameters_staggering_cap": [0],
            "solution_staggering_applied": [0]
        })
        exploded_data = pd.concat([exploded_data, null_pont])
        sns.boxplot(
            x="instance_parameters_staggering_cap",
            y="solution_staggering_applied",
            data=exploded_data,
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

        # Save boxplot
        file_name = f"staggering_applied_boxplot_{label.lower()}"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)
        tikzplotlib.save(output_dir / f"{file_name}.tex")
        plt.close()
        print(f"Boxplot for {label} saved.".center(50))

    # Generate plots for LC
    generate_plots(lc_data, "LC")

    # Generate plots for HC
    generate_plots(hc_data, "HC")

    print("\n" + "=" * 50)
    print("Completed get_staggering_analysis_plots".center(50))
    print("=" * 50 + "\n")
