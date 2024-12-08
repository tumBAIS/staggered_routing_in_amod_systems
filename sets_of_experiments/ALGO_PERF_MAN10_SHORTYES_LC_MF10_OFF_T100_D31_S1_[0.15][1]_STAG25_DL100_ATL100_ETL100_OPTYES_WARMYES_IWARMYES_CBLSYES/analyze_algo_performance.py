import sys
from sets_of_experiments.tools import import_results
from pathlib import Path

PATH_TO_RESULTS = Path(__file__).parent / "results"

if __name__ == "__main__":
    results_df = import_results(PATH_TO_RESULTS)
    x = 0
