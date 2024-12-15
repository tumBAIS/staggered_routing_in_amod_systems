import numpy as np
import pandas as pd
import json
from pathlib import Path
from pandas import DataFrame
import warnings
from tabulate import tabulate

# Suppress the specific FutureWarning about applymap
warnings.filterwarnings(
    "ignore",
    message="DataFrame.applymap has been deprecated.*",
    category=FutureWarning
)


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


from pprint import pprint


def set_arc_to_node_mapping(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a mapping of arc IDs to corresponding node pairs and add it as a new column in the DataFrame.
     """

    def create_mapping(arc_routes, node_routes):
        """
        Create a dictionary mapping arcs to node pairs for a single pair of arc and node routes.
        """
        arc_to_node = {}
        for x in range(len(arc_routes)):  # Iterate over all routes
            for y in range(len(arc_routes[x]) - 1):  # Ignore the last arc (dummy arc)
                arc = arc_routes[x][y]
                node_pair = (node_routes[x][y], node_routes[x][y + 1])  # Get corresponding node pair
                arc_to_node[arc] = node_pair
        return arc_to_node

    # Apply the mapping creation for each row
    results_df['arc_to_node_mapping'] = results_df.apply(
        lambda row: create_mapping(row['instance_trip_routes'], row['instance_node_based_trip_routes']),
        axis=1
    )

    return results_df


def assign_congestion_level(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign congestion level to the DataFrame based on the `instance_parameters_max_flow_allowed` column.
    """
    # Get the unique values from the column
    unique_values = results_df['instance_parameters_max_flow_allowed'].unique()

    if len(unique_values) == 2:
        # Sort the unique values to determine the highest and lowest
        low_value, high_value = sorted(unique_values)

        # Assign congestion levels
        results_df['congestion_level'] = results_df['instance_parameters_max_flow_allowed'].apply(
            lambda x: "HC" if x == high_value else "LC"
        )
    else:
        # Handle cases with not exactly two unique values
        results_df['congestion_level'] = None  # or pd.NA for pandas-style missing values

    return results_df


import pandas as pd
import numpy as np


def print_arc_delays_distribution(results_df):
    """
    Process and print arc delay statistics for the given dataframe of experiments.

    Parameters:
        results_df (pd.DataFrame): Dataframe containing experiment results with relevant columns.
    """
    # Filter only the OFFLINE experiments (solver_parameters_epoch_size == 60)
    offline_df = results_df[results_df['solver_parameters_epoch_size'] == 60]

    # Split the dataframe into low and high flow constraint groups
    lc_df = offline_df[offline_df['instance_parameters_max_flow_allowed'] <= \
                       offline_df['instance_parameters_max_flow_allowed'].median()]
    hc_df = offline_df[offline_df['instance_parameters_max_flow_allowed'] > \
                       offline_df['instance_parameters_max_flow_allowed'].median()]

    # Helper function to process a dataframe
    def process_df(group_df, label):
        stats_dict = {}

        for index, row in group_df.iterrows():
            # Retrieve required columns
            arc_delays = row['status_quo_delays_on_arcs']  # list[list[float]]
            trip_routes = row['instance_trip_routes']  # list[list[int]]
            arc_mapping = row['arc_to_node_mapping']  # dict[int:tuple]

            # Flatten the list of delays and their corresponding arcs
            total_delays = []
            arc_names = []
            for route_idx, route_delays in enumerate(arc_delays):
                for arc_idx, delay in enumerate(route_delays):
                    total_delays.append(delay)
                    arc_id = trip_routes[route_idx][arc_idx]  # Get the arc ID from the trip routes
                    arc_names.append(arc_mapping.get(arc_id, ("Unknown",)))

            # Calculate statistics for total delays
            stats = {
                'Sum': round(np.sum(total_delays), 2),
                'Min': round(np.min(total_delays), 2),
                'Max': round(np.max(total_delays), 2),
                'Mean': round(np.mean(total_delays), 2),
                'Median': round(np.median(total_delays), 2),
                '10th Percentile': round(np.percentile(total_delays, 10), 2),
                '90th Percentile': round(np.percentile(total_delays, 90), 2),
            }

            stats_dict[index] = stats

        # Create a DataFrame for all statistics
        stats_df = pd.DataFrame(stats_dict).T

        # Sort the table by the sum of delays in descending order
        stats_df = stats_df.sort_values(by='Sum', ascending=False)

        # Transpose the table for better readability
        transposed_stats_df = stats_df.T

        # Remove column names
        transposed_stats_df.columns = ["" for _ in transposed_stats_df.columns]

        # Print the table with pretty borders
        print(f"\n--- {label} Congestion Instances Arc Total Delays Statistics ---\n")
        print(tabulate(transposed_stats_df, headers='keys', tablefmt='fancy_grid'))

    # Process both dataframes
    process_df(lc_df, "Low")
    process_df(hc_df, "High")


def get_results_df(path_to_results: Path) -> pd.DataFrame:
    """
    Imports results from JSON files located in subdirectories of a given path.
    """
    print("\n" + "=" * 50)
    print("Starting get_results_df function".center(50))
    print("=" * 50 + "\n")

    # Step 1: Import results into a DataFrame
    print("Step 1: Importing results from files...")
    results_df = import_results_df_from_files(path_to_results)
    print(f"Results imported. DataFrame shape: {results_df.shape}")

    # Step 2: Flatten the DataFrame
    print("\nStep 2: Flattening the results DataFrame...")
    results_df = flatten_results_df(results_df)
    print(f"Results flattened. DataFrame shape: {results_df.shape}")

    # Step 3: Assign instance parameter IDs
    print("\nStep 3: Assigning instance parameter IDs...")
    results_df = assign_congestion_level(results_df)
    results_df = set_instance_parameters_id(results_df)
    print(f"Instance parameters assigned. DataFrame shape: {results_df.shape}")

    # Step 3: Assign instance parameter IDs
    print("\nStep 3: Creating arc to node mapping...")
    results_df = set_arc_to_node_mapping(results_df)
    print_arc_delays_distribution(results_df)
    print(f"Arc mapping assigned. DataFrame shape: {results_df.shape}")

    print("\n" + "=" * 50)
    print("Completed get_results_df function".center(50))
    print("=" * 50 + "\n")
    raise RuntimeError
    return results_df


def filter_non_comparable_experiments(results_df: pd.DataFrame, n_experiments_required: int = 2) -> pd.DataFrame:
    # Count occurrences of each `instance_parameters_id`
    counts = results_df['instance_parameters_id'].value_counts()

    # Filter IDs that meet the minimum required experiments
    valid_ids = counts[counts >= n_experiments_required].index

    # Filter the DataFrame to keep only rows with valid IDs
    filtered_df = results_df[results_df['instance_parameters_id'].isin(valid_ids)]

    return filtered_df
