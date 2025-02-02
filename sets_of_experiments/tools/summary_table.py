import pandas as pd
import os
from pathlib import Path


def get_summary_table(results_df: pd.DataFrame, path_to_tables: Path) -> None:
    # Step 1: Retain only the offline experiments
    print("Filtering offline experiments...")
    offline_df = results_df[results_df["solver_parameters_epoch_size"] == 60]
    print(f"Retained {len(offline_df)} offline experiments.")

    # Step 2: Split the DataFrame into LC and HC categories
    print("Splitting data into LC and HC...")
    lc_df = offline_df[offline_df["congestion_level"] == "LC"]
    hc_df = offline_df[offline_df["congestion_level"] == "HC"]
    print(f"LC experiments: {len(lc_df)}, HC experiments: {len(hc_df)}")

    # Helper function to calculate statistics
    def calculate_statistics(df):
        total_number_of_arcs_after_splitting = df["instance_conflicting_sets"].apply(
            lambda x: sum(1 for _ in x) - 1
        )
        num_conflicting_sets = df["instance_conflicting_sets"].apply(
            lambda x: sum(1 for sublist in x if len(sublist) > 0)
        )

        # New metrics: number_of_nodes and number_of_node_pairs
        number_of_nodes = df["number_of_nodes"]
        number_of_node_pairs = df["number_of_node_pairs"]

        return {
            "Min": [
                int(number_of_node_pairs.min()),
                int(number_of_nodes.min()),
                int(total_number_of_arcs_after_splitting.min()),
                int(num_conflicting_sets.min())
            ],
            "Max": [
                int(number_of_node_pairs.max()),
                int(number_of_nodes.max()),
                int(total_number_of_arcs_after_splitting.max()),
                int(num_conflicting_sets.max())
            ],
            "Avg": [
                int(number_of_node_pairs.mean()),
                int(number_of_nodes.mean()),
                int(total_number_of_arcs_after_splitting.mean()),
                int(num_conflicting_sets.mean())
            ],
        }

    # Step 3: Calculate statistics for LC and HC
    print("Calculating statistics for LC and HC...")
    lc_summary_data = calculate_statistics(lc_df)
    hc_summary_data = calculate_statistics(hc_df)

    # Metrics labels for LaTeX formatting
    metrics = [
        r"$|{\SetArcs}|$",
        r"$|{\SetNodes}|$",
        r"$|{\SetArcs}|^{\text{m}}$",
        r"$|\hat{\mathcal{A}}|^{\text{m}}$",
    ]

    # Step 4: Combine LC and HC into a single table for LaTeX formatting
    print("Combining LC and HC data into a single table...")
    lc_summary_table = pd.DataFrame(lc_summary_data, index=metrics)
    hc_summary_table = pd.DataFrame(hc_summary_data, index=metrics)

    # Step 5: Generate LaTeX code for the table
    print("Generating LaTeX table...")
    latex_table = """\\begin{tabularx}{\\textwidth}{l|XXX|XXX}
                    \\toprule
                     & \\multicolumn{3}{c}{LC} & \\multicolumn{3}{c}{HC} \\
                    \\cmidrule(lr){2-4} \\cmidrule(lr){5-7}
                     & Min & Max & Avg & Min & Max & Avg \\
                    \\midrule
                    """

    for metric, lc_values, hc_values in zip(metrics, lc_summary_table.values, hc_summary_table.values):
        latex_table += (
            f"{metric} & {' & '.join(map(str, lc_values))} & {' & '.join(map(str, hc_values))} \\\\ \n"
        )

    latex_table += "\\bottomrule\n\\end{tabularx}"

    # Step 6: Save the table to files
    print("Saving table to files...")
    output_dir = Path(path_to_tables)
    os.makedirs(output_dir, exist_ok=True)

    latex_path = output_dir / "summary_table.tex"
    with open(latex_path, "w", encoding="utf-8") as latex_file:
        latex_file.write(latex_table)

    print("Summary table generation complete.")
