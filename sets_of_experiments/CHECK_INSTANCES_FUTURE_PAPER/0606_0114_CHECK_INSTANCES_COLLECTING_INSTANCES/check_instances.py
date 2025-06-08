import os

from sets_of_experiments.tools.chck_instances_future_paper.load import (collect_jsons,
                                                                        add_additional_columns_to_instances_df,
                                                                        get_boxplot_status_quo_total_delay_hours,
                                                                        save_status_quo_table_as_html)
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_DFS = Path(__file__).parent / "dfs"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
PATH_TO_TABLES = Path(__file__).parent / "tables"
PATH_TO_NETWORKS = Path(__file__).parent / "networks"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)
os.makedirs(PATH_TO_TABLES, exist_ok=True)

if __name__ == "__main__":
    solutions_df = collect_jsons(PATH_TO_RESULTS, PATH_TO_DFS)
    solutions_df = add_additional_columns_to_instances_df(solutions_df)
    get_boxplot_status_quo_total_delay_hours(solutions_df, PATH_TO_FIGURES)
    save_status_quo_table_as_html(solutions_df, PATH_TO_TABLES)
