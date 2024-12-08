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


def set_instance_parameters_id(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns unique IDs to each unique `instance_parameters` row in the flattened DataFrame.

    Args:
        results_df (pd.DataFrame): The input DataFrame with flattened `instance_parameters` columns.

    Returns:
        pd.DataFrame: A DataFrame with a new column `instance_parameters_id` indicating the unique ID.
    """

    def normalize_value(value):
        """
        Normalize unhashable types to hashable equivalents.
        """
        if isinstance(value, list):
            return tuple(value)  # Convert list to tuple
        return value  # Leave other types unchanged

    # Select instance_parameter columns and normalize their values
    instance_columns = results_df.filter(like='instance_parameters_')
    normalized_instance_rows = instance_columns.applymap(normalize_value).apply(tuple, axis=1)

    # Map unique rows to IDs
    unique_instance_map = {value: idx for idx, value in enumerate(pd.unique(normalized_instance_rows))}

    # Assign IDs to a new column
    results_df['instance_parameters_id'] = normalized_instance_rows.map(unique_instance_map)

    return results_df


def get_results_df(path_to_results: Path) -> pd.DataFrame:
    """
    Imports results from JSON files located in subdirectories of a given path.
    """
    results_df = import_results_df_from_files(path_to_results)
    results_df = flatten_results_df(results_df)
    results_df = set_instance_parameters_id(results_df)
    return results_df


def filter_non_comparable_experiments(results_df: pd.DataFrame, n_experiments_required: int = 2) -> pd.DataFrame:
    # Count occurrences of each `instance_parameters_id`
    counts = results_df['instance_parameters_id'].value_counts()

    # Filter IDs that meet the minimum required experiments
    valid_ids = counts[counts >= n_experiments_required].index

    # Filter the DataFrame to keep only rows with valid IDs
    filtered_df = results_df[results_df['instance_parameters_id'].isin(valid_ids)]

    return filtered_df
