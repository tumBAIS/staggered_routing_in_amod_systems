import os
from sets_of_experiments.tools import get_results_df
from sets_of_experiments.tools.no_ls_comparison_boxplots import get_no_ls_comparison_boxplot
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"
PATH_TO_FIGURES = Path(__file__).parent / "figures"
os.makedirs(PATH_TO_FIGURES, exist_ok=True)

if __name__ == "__main__":
    results_df = get_results_df(PATH_TO_RESULTS)
    get_no_ls_comparison_boxplot(results_df, PATH_TO_FIGURES)
