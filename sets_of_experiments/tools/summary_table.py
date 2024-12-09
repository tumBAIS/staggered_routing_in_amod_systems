import pandas as pd
import os
from pathlib import Path


def get_summary_table(results_df: pd.DataFrame, path_to_tables: Path) -> None:
    # Step 1: Retain only the offline experiments
    print("Filtering offline experiments...")
    offline_df = results_df[results_df["solver_parameters_epoch_size"] == 60]
    print(f"Retained {len(offline_df)} offline experiments.")

    # Step 2: Calculate required statistics
    print("Calculating statistics...")

    # Status Quo Total Delay (\bar{Z})
    total_delays = offline_df["status_quo_total_delay"]

    # Number of instance_conflicting_sets lists with at least one value (\vert \hat{A} \vert)
    num_conflicting_sets = offline_df["instance_conflicting_sets"].apply(
        lambda x: sum(len(sublist) > 0 for sublist in x)
    )

    # Length of the longest list in instance_conflicting_sets (\vert R_a \vert^{\text{MAX}})
    longest_conflicting_set = offline_df["instance_conflicting_sets"].apply(
        lambda x: max((len(sublist) for sublist in x), default=0)
    )

    # Summary calculations (Min, Max, Avg)
    summary_data = {
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

    # Metrics with LaTeX formatting
    metrics = [
        r"$\bar{Z} \, \mathrm{[min]}$",  # Bar over Z with units
        r"$\vert \hat{A} \vert$",  # Absolute value with a hat over A
        r"$\vert R_a \vert^{\text{MAX}}$"  # Superscript MAX for R_a
    ]

    # Step 3: Create the summary table
    print("Creating summary table...")
    summary_table = pd.DataFrame(
        summary_data,
        index=metrics
    )

    # Step 4: Save the table as HTML and LaTeX
    print("Saving table to files...")
    output_dir = Path(path_to_tables)
    os.makedirs(output_dir, exist_ok=True)

    html_path = output_dir / "summary_table.html"
    latex_path = output_dir / "summary_table.tex"

    # Save as HTML
    summary_table.to_html(html_path, border=0)

    # Save as LaTeX
    with open(latex_path, "w", encoding="utf-8") as latex_file:
        latex_file.write(
            summary_table.to_latex(escape=False, column_format="lccc")
        )

    print("Summary table generation complete.")
