import pandas as pd
import json
from pathlib import Path


def import_results(path_to_results: Path) -> pd.DataFrame:
    """
    Imports results from JSON files located in subdirectories of a given path.
    """
    all_results = []

    # Iterate over all folders in the given path
    for folder in path_to_results.iterdir():
        if folder.is_dir():  # Check if it is a directory
            results_file = folder / "results.json"
            if results_file.exists():  # Check if results.json exists
                with open(results_file, "r") as file:
                    try:
                        data = json.load(file)
                        data['folder_name'] = folder.name  # Include folder name for reference
                        all_results.append(data)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON in {results_file}")

    # Convert the list of dictionaries to a DataFrame
    return pd.DataFrame(all_results)
