import datetime
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

warnings.filterwarnings("ignore", message="the convert_dtype parameter is deprecated and will be removed in a future version")

def _setPickUpAndDropOffLocations(taxiRides: DataFrame, manhattanGraph: DiGraph) -> None:
    """find the closest node of graph to pickup and dropoff points of rides"""
    pickupLocations: Series = _getNearestNodes(taxiRides["Projected Pickup Point"], manhattanGraph,
                                               maximumMetersRadius=5000)
    taxiRides["Pickup locations"] = pickupLocations
    dropoffLocations: Series = _getNearestNodes(taxiRides["Projected Dropoff Point"], manhattanGraph,
                                                maximumMetersRadius=5000)
    taxiRides["Dropoff locations"] = dropoffLocations
    "remove records with coincident pickup and dropoffs"
    ridesBefore = len(taxiRides)
    taxiRides.drop(taxiRides[taxiRides["Pickup locations"] == taxiRides["Dropoff locations"]].index,
                   inplace=True)
    taxiRides.reset_index(inplace=True)
    ridesAfter = len(taxiRides)
    print(
        f"Removed {ridesBefore - ridesAfter} vehicles with coincident "
        f"pickup and dropoffs - Current number of trips: {len(taxiRides)}"
    )
    return


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
    pathToData = inputData.path_to_instance + fr"/instance.json"
    if not os.path.exists(f"{pathToData}"):
        raise RuntimeError(f"no instance in  {pathToData}")
    rides_df: DataFrame = pd.read_json(f"{pathToData}")
    print(f"Initial number of trips: {len(rides_df)}")
    _setPickUpAndDropOffLocations(rides_df, graph)
    return rides_df


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
