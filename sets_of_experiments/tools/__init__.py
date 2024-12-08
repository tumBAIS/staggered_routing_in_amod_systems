import pandas as pd
import json
from pathlib import Path
from pandas import DataFrame


def import_results_df_from_files(path_to_results: Path):
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


def flatten_results_df(results_df: DataFrame) -> DataFrame:
    columns_to_flatten = ['instance_parameters', 'solver_parameters', 'instance', 'status_quo', 'solution']

    for col in columns_to_flatten:
        if col in results_df.columns:
            # Extract and normalize the dictionary column into separate columns
            expanded_columns = pd.json_normalize(results_df[col].dropna())
            # Prefix the new columns with the original column name
            expanded_columns.columns = [f"{col}_{key}" for key in expanded_columns.columns]
            # Concatenate the expanded columns with the original DataFrame
            results_df = pd.concat([results_df.drop(columns=[col]), expanded_columns], axis=1)

    return results_df


def get_results_df(path_to_results: Path) -> pd.DataFrame:
    """
    Imports results from JSON files located in subdirectories of a given path.
    """
    results_df = import_results_df_from_files(path_to_results)
    results_df = flatten_results_df(results_df)

    return results_df
