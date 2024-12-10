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
        total_delays = df["status_quo_total_delay"]
        num_conflicting_sets = df["instance_conflicting_sets"].apply(
            lambda x: sum(len(sublist) > 0 for sublist in x)
        )
        longest_conflicting_set = df["instance_conflicting_sets"].apply(
            lambda x: max((len(sublist) for sublist in x), default=0)
        )

        return {
            "Min": [
                int(total_delays.min()),
                int(num_conflicting_sets.min()),
                int(longest_conflicting_set.min())
            ],
            "Max": [
                int(total_delays.max()),
                int(num_conflicting_sets.max()),
                int(longest_conflicting_set.max())
            ],
            "Avg": [
                int(total_delays.mean()),
                int(num_conflicting_sets.mean()),
                int(longest_conflicting_set.mean())
            ],
        }

    # Step 3: Calculate statistics for LC and HC
    print("Calculating statistics for LC and HC...")
    lc_summary_data = calculate_statistics(lc_df)
    hc_summary_data = calculate_statistics(hc_df)

    # Metrics with LaTeX formatting
    metrics = [
        r"$\bar{Z} \, \mathrm{[min]}$",  # Bar over Z with units
        r"$\vert \hat{A} \vert$",  # Absolute value with a hat over A
        r"$\vert R_a \vert^{\text{MAX}}$"  # Superscript MAX for R_a
    ]

    # Step 4: Combine LC and HC into a single table
    print("Combining LC and HC data into a single table...")
    lc_summary_table = pd.DataFrame(lc_summary_data, index=metrics)
    hc_summary_table = pd.DataFrame(hc_summary_data, index=metrics)

    combined_table = pd.concat(
        [lc_summary_table, hc_summary_table],
        keys=["LC", "HC"],
        axis=1
    )

    # Step 5: Save the table as HTML and LaTeX
    print("Saving table to files...")
    output_dir = Path(path_to_tables)
    os.makedirs(output_dir, exist_ok=True)

    html_path = output_dir / "summary_table.html"
    latex_path = output_dir / "summary_table.tex"

    # Save as HTML
    combined_table.to_html(html_path, border=0)

    # Save as LaTeX
    with open(latex_path, "w", encoding="utf-8") as latex_file:
        latex_file.write(
            combined_table.to_latex(escape=False, column_format="lcccccc")
        )

    print("Summary table generation complete.")
