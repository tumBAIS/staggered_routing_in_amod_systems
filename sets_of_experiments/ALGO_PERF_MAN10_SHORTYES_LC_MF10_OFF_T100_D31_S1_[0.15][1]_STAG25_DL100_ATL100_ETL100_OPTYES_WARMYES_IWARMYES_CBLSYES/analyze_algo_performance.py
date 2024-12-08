import sys
from sets_of_experiments.tools import get_results_df
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"

if __name__ == "__main__":
    results_df = get_results_df(PATH_TO_RESULTS)
    x = 0
