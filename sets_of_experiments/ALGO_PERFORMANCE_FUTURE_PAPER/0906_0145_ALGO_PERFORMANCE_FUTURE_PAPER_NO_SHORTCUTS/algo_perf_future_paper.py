import os

from sets_of_experiments.tools.algo_perf_future_paper.load import (collect_results_json,
                                                                   add_additional_columns_to_df,
                                                                   plot_delay_reductions,
                                                                   check_if_all_solutions_are_feasible,
                                                                   filter_comparable_experiments)
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_DFS = Path(__file__).parent / "dfs"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
PATH_TO_TABLES = Path(__file__).parent / "tables"
PATH_TO_NETWORKS = Path(__file__).parent / "networks"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)
os.makedirs(PATH_TO_TABLES, exist_ok=True)

if __name__ == "__main__":
    solutions_df = collect_results_json(PATH_TO_RESULTS, PATH_TO_DFS)
    solutions_df = add_additional_columns_to_df(solutions_df)
    solutions_df = filter_comparable_experiments(solutions_df)
    check_if_all_solutions_are_feasible(solutions_df)
    solutions_df = plot_delay_reductions(solutions_df, PATH_TO_FIGURES)
