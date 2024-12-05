import datetime
import json
import os.path

from networkx import DiGraph
import pandas as pd
import numpy as np
import momepy
from scipy.spatial import cKDTree
from geopandas import GeoDataFrame
from pandas import DataFrame, Series
from inputData import InputData
import warnings
from instance_generator.computer import InstanceComputer

warnings.filterwarnings("ignore",
                        message="the convert_dtype parameter is deprecated and will be removed in a future version")


# def _setPickUpAndDropOffLocations(taxiRides: DataFrame, manhattanGraph: DiGraph) -> None:
#     """find the closest node of graph to pickup and dropoff points of rides"""
#     pickupLocations: Series = _getNearestNodes(taxiRides["Projected Pickup Point"], manhattanGraph,
#                                                maximumMetersRadius=5000)
#     taxiRides["Pickup locations"] = pickupLocations
#     dropoffLocations: Series = _getNearestNodes(taxiRides["Projected Dropoff Point"], manhattanGraph,
#                                                 maximumMetersRadius=5000)
#     taxiRides["Dropoff locations"] = dropoffLocations
#     "remove records with coincident pickup and dropoffs"
#     ridesBefore = len(taxiRides)
#     taxiRides.drop(taxiRides[taxiRides["Pickup locations"] == taxiRides["Dropoff locations"]].index,
#                    inplace=True)
#     taxiRides.reset_index(inplace=True)
#     ridesAfter = len(taxiRides)
#     print(
#         f"Removed {ridesBefore - ridesAfter} vehicles with coincident "
#         f"pickup and dropoffs - Current number of trips: {len(taxiRides)}"
#     )
#     return


# https://gis.stackexchange.com/questions/222315/finding-nearest-point-in-other-geodataframe-using-geopandas
def _getNearestNodes(projectedGeometriesNodes: Series, graph: DiGraph, maximumMetersRadius=np.inf) -> Series:
    graph.graph["approach"] = "primal"  # endpoints as nodes and LineStrings as edges
    graphNodes: GeoDataFrame = momepy.nx_to_gdf(graph, points=True, lines=False, spatial_weights=False)
    graphNodes.set_index(pd.Index(list(graph.nodes)), inplace=True)  # save info on id nodes

    nA = np.array(list(projectedGeometriesNodes.apply(lambda x: (x["x"], x["y"]))))
    nB = np.array(list(graphNodes.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(nB)
    dist, idx = btree.query(nA, k=1, distance_upper_bound=maximumMetersRadius)
    gdB_nearest = graphNodes.iloc[idx].index
    nearestNodes = pd.Series(gdB_nearest)
    return nearestNodes


def import_rides_df(inputData: InputData, graph: DiGraph) -> DataFrame:
    path_to_instance = inputData.path_to_instance
    if not os.path.exists(f"{path_to_instance}"):
        InstanceComputer(inputData).run()
    # Load JSON data into a Python dictionary
    with open(path_to_instance, 'r') as file:
        data = json.load(file)

    # Normalize the part of the JSON containing the trip data
    # Assuming all trip data keys follow the pattern 'trip_x'
    trip_data = [data.pop(key) for key in list(data.keys()) if key.startswith('trip_')]

    # Convert the list of trip data into a DataFrame
    trips_df = pd.json_normalize(trip_data)

    print(f"Initial number of trips: {len(trips_df)}")
    # _setPickUpAndDropOffLocations(trips_df, graph)

    path_to_routes = inputData.path_to_routes

    with open(path_to_routes, 'r') as file:
        routes_data = json.load(file)

        # Select only relevant keys from routes data
    relevant_keys = ['path', 'origin', 'destination', 'origin_coords', 'destination_coords']
    filtered_routes_data = [{key: route[key] for key in relevant_keys if key in route} for route in routes_data]

    # Convert filtered routes data to a DataFrame
    routes_df = pd.DataFrame(filtered_routes_data)

    # Ensure that the DataFrame from routes_data has the same order and length as trips_df
    if len(routes_df) != len(trips_df):
        raise ValueError("The number of routes does not match the number of trips.")

    # Combine trips_df with routes_df
    combined_df = pd.concat([trips_df, routes_df], axis=1)

    return combined_df


def getReleaseTimesAndArrivalTimesDataset(taxiRides: DataFrame):
    """
    Retrieves release times and arrival times from the taxi rides dataset.

    """

    releaseTimes = [row.Trip_Pickup_DateTime for _, row in taxiRides.iterrows()]

    arrivalTimesDataset = [row.Trip_Dropoff_DateTime for _, row in taxiRides.iterrows()]

    totalTravelTimeSystemFromDataPoints = sum(
        [arrivalTimesDataset[i] - releaseTimes[i] for i in range(len(releaseTimes))]
    )
    if arrivalTimesDataset[0] != -1:
        print("Dataset total travel time:", round(totalTravelTimeSystemFromDataPoints / 3600, 2), "[h]")

    return releaseTimes, arrivalTimesDataset
