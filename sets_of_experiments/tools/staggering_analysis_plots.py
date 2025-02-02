import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
from matplotlib import MatplotlibDeprecationWarning
import tikzplotlib
from matplotlib.ticker import FuncFormatter
import re

# Suppress specific MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)


def remove_trailing_zeros(x, _):
    """Remove trailing zeros from tick labels."""
    return "%g" % x


def fix_tex_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Remove trailing .0 from tick labels (e.g., "10.0" -> "10")
    content = re.sub(r'(\d+)\.0\b', r'\1', content)

    # Replace escaped superscript symbols with proper LaTeX math symbols
    content = content.replace(r"\^", "^")  # Handle escaped superscripts
    content = content.replace(r"\$", "$")  # Handle escaped dollar

    with open(file_path, 'w') as file:
        file.write(content)


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

    # Calculate the staggering applied column
    results_df['solution_staggering_applied'] = results_df.apply(
        lambda row: [sol - sq for sol, sq in zip(row['solution_start_times'], row['status_quo_start_times'])],
        axis=1
    )

    # Split the data into LC and HC
    lc_data = results_df[results_df["congestion_level"] == "LC"].copy()
    hc_data = results_df[results_df["congestion_level"] == "HC"].copy()

    for data in [lc_data, hc_data]:
        data.loc[:, "solution_total_delay"] = data["solution_total_delay"] / 60  # Convert to minutes
        data.loc[:, "solution_staggering_applied"] = data["solution_staggering_applied"].apply(
            lambda x: [v / 60 for v in x] if isinstance(x, list) else x
        )

    def generate_plots(data, label):
        output_dir = path_to_figures / "staggering_analysis_plots"
        os.makedirs(output_dir, exist_ok=True)

        # Bar plot
        plt.figure(figsize=(1.9685, 1.9685))  # 5 cm height in inches
        sns.barplot(
            x="instance_parameters_staggering_cap",
            y="solution_total_delay",
            data=data,
            color="gray",
            edgecolor="black"
        )
        plt.gca().yaxis.set_major_formatter(FuncFormatter(remove_trailing_zeros))
        plt.xlabel(r"\$\zeta^{\mathrm{MAX}}\$ [%]")
        plt.ylabel(r"\$Z(\pi)\$ [min]")
        plt.grid(axis='y', linestyle='--', color='gray', alpha=0.7)
        plt.tight_layout()
        file_name = f"staggering_total_delay_barplot_{label.lower()}"
        tex_file_path = output_dir / f"{file_name}.tex"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)
        tikzplotlib.save(tex_file_path, axis_width="\\StaggeringAnalysisWidth",
                         axis_height="\\StaggeringAnalysisHeight")
        fix_tex_file(tex_file_path)  # Fix LaTeX issues
        plt.close()

        # Boxplot
        plt.figure(figsize=(1.9685, 1.9685))  # 5 cm height in inches
        exploded_data = data.explode("solution_staggering_applied").dropna(subset=["solution_staggering_applied"])
        exploded_data = exploded_data[exploded_data["solution_staggering_applied"] > 1e-4]
        null_point = pd.DataFrame({
            "instance_parameters_staggering_cap": [0],
            "solution_staggering_applied": [0]
        })
        exploded_data = pd.concat([exploded_data, null_point])
        # Assuming remove_trailing_zeros and other functions are already defined
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

        # Set y-axis limits and ticks
        plt.gca().set_ylim(0, 11)  # Set the y-axis range from 0 to 11
        plt.gca().set_yticks([0, 5, 10])  # Set y-ticks to 0, 5, and 10
        plt.gca().yaxis.set_major_formatter(FuncFormatter(remove_trailing_zeros))

        # Axis labels
        plt.xlabel(r"\$\zeta^{\mathrm{MAX}}\$ [%]")
        plt.ylabel(r"\$\sigma^r\$ [min]")

        # Grid settings
        plt.grid(axis='y', linestyle='--', color='gray', alpha=0.7)

        # Adjust layout
        plt.tight_layout()

        # Save figures
        file_name = f"staggering_applied_boxplot_{label.lower()}"
        tex_file_path = output_dir / f"{file_name}.tex"
        plt.savefig(output_dir / f"{file_name}.jpeg", format="jpeg", dpi=300)

        # Save as TikZ for LaTeX
        tikzplotlib.save(tex_file_path, axis_width="\\StaggeringAnalysisWidth",
                         axis_height="\\StaggeringAnalysisHeight")

        # Fix LaTeX issues in the TikZ file
        fix_tex_file(tex_file_path)

        # Close the plot
        plt.close()

    generate_plots(lc_data, "LC")
    generate_plots(hc_data, "HC")

    print("\n" + "=" * 50)
    print("Completed get_staggering_analysis_plots".center(50))
    print("=" * 50 + "\n")
