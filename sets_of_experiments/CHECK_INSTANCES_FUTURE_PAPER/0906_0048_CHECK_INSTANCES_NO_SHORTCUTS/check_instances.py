import os

from sets_of_experiments.tools.check_instances_future_paper.load import (plot_status_quo_arc_delays_per_flow,
                                                                         get_boxplot_status_quo_total_delay_hours,
                                                                         save_status_quo_tables_by_flow)
from sets_of_experiments.tools.algo_perf_future_paper.load import (collect_results_json,
                                                                   add_additional_columns_to_df)

from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_DFS = Path(__file__).parent / "dfs"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
PATH_TO_TABLES = Path(__file__).parent / "tables"
PATH_TO_NETWORKS = Path(__file__).parent / "networks"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)
os.makedirs(PATH_TO_TABLES, exist_ok=True)

if __name__ == "__main__":
    # Load all solutions
    solutions_df = collect_results_json(PATH_TO_RESULTS, PATH_TO_DFS)

    # Filter by staggering cap
    if solutions_df["instance_parameters_staggering_cap"].unique().size > 1:
        smallest_staggering_cap = solutions_df["instance_parameters_staggering_cap"].unique()[0]
        solutions_df = solutions_df[solutions_df["instance_parameters_staggering_cap"] == smallest_staggering_cap]
        solutions_df = solutions_df[solutions_df["instance_parameters_max_flow_allowed"] < 20]

    solutions_df = add_additional_columns_to_df(solutions_df, solutions_computed=False)
    plot_status_quo_arc_delays_per_flow(solutions_df, PATH_TO_FIGURES / "boxplots_arc_delays")
    get_boxplot_status_quo_total_delay_hours(solutions_df, PATH_TO_FIGURES / "aggregated_boxplots")
    save_status_quo_tables_by_flow(solutions_df, PATH_TO_TABLES)
