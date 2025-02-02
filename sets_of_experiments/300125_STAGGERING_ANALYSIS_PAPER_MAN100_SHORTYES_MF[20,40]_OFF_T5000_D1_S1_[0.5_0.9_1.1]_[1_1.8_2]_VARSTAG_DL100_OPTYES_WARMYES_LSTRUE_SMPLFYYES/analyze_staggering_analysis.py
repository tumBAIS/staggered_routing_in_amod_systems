import os
from sets_of_experiments.tools import get_results_df, filter_non_comparable_experiments
from sets_of_experiments.tools.staggering_analysis_plots import get_staggering_analysis_plots
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)

if __name__ == "__main__":
    results_df = get_results_df(PATH_TO_RESULTS)
    get_staggering_analysis_plots(results_df, PATH_TO_FIGURES)
