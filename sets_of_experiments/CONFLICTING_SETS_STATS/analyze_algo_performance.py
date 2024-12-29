import os
from sets_of_experiments.tools import get_results_df, filter_non_comparable_experiments
from sets_of_experiments.tools.algo_performance_boxplots import get_algo_performance_boxplots
from sets_of_experiments.tools.mip_bounds_boxplots import get_mip_bounds_boxplots
from sets_of_experiments.tools.arc_congestion_distribution_barplot import get_arc_congestion_distribution_barplot
from sets_of_experiments.tools.heatmaps import get_congestion_heatmaps
from sets_of_experiments.tools.summary_table import get_summary_table
from sets_of_experiments.tools.barplot_conflicting_sets import get_barplot_conflicting_sets
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
PATH_TO_TABLES = Path(__file__).parent / "tables"
PATH_TO_NETWORKS = Path(__file__).parent / "networks"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)
os.makedirs(PATH_TO_TABLES, exist_ok=True)

if __name__ == "__main__":
    results_df = get_results_df(PATH_TO_RESULTS)
    results_df = filter_non_comparable_experiments(results_df, n_experiments_required=2)
    get_summary_table(results_df, PATH_TO_TABLES)
    get_barplot_conflicting_sets(results_df, PATH_TO_FIGURES, verbose=True)
    get_algo_performance_boxplots(results_df, PATH_TO_FIGURES, verbose=True)
    get_mip_bounds_boxplots(results_df, PATH_TO_FIGURES, verbose=True)
    get_arc_congestion_distribution_barplot(results_df, PATH_TO_FIGURES, verbose=True)
    get_congestion_heatmaps(results_df, PATH_TO_FIGURES, PATH_TO_NETWORKS)
