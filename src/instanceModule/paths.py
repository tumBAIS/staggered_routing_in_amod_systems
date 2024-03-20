import collections
import typing
from itertools import tee

import networkx as nx
from networkx import DiGraph
from pandas import DataFrame


def _removeUnreachablePaths(taxiRidesWithPuDo: DataFrame, indicesPathsToRemove: list[int]):
    """remove unreachable paths from pickup locations and dropoff locations"""
    for index in indicesPathsToRemove:
        taxiRidesWithPuDo.drop(index, inplace=True)
    taxiRidesWithPuDo.reset_index(inplace=True, drop=True)
    print(
        f"Removed {len(indicesPathsToRemove)} unreachable/too short path(s) - Current number of trips: {len(taxiRidesWithPuDo)}")


def getNodeBasedShortestPaths(taxiRidesWithPuDo: DataFrame, manhattanGraph: DiGraph) -> list[list[int]]:
    """Compute node-based-shortest-paths and remove records associated to unreachable paths"""
    print("Computing the shortest paths ... ", end="")
    nodeBasedShortestPaths = []
    indicesPathsToRemove = []
    for idxRecord in range(len(taxiRidesWithPuDo)):
        try:
            path = nx.shortest_path(manhattanGraph, taxiRidesWithPuDo.iloc[idxRecord]["Pickup locations"],
                                    taxiRidesWithPuDo.iloc[idxRecord]["Dropoff locations"], weight='length')
            total_length = sum(manhattanGraph[path[i]][path[i + 1]]['length'] for i in range(len(path) - 1))
            # if total_length < 10000:
            #     indicesPathsToRemove.append(idxRecord)
            #     continue
        except:
            indicesPathsToRemove.append(idxRecord)
            continue
        nodeBasedShortestPaths.append(list(path))
    print("done!")
    if indicesPathsToRemove:
        _removeUnreachablePaths(taxiRidesWithPuDo, indicesPathsToRemove)
    print("Total nodes in shortest paths: ", sum([len(path) for path in nodeBasedShortestPaths]))
    return nodeBasedShortestPaths


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def getArcBasedShortestPathsOriginalIDs(nodeBasedShortestPaths: list[list[int]]) -> list[list[tuple[int, int]]]:
    arcBasedShortestPathsOriginalIDs = [[(u, v) for (u, v) in pairwise(pathNodes)] for pathNodes in
                                        nodeBasedShortestPaths]
    return arcBasedShortestPathsOriginalIDs


def _removeRepetitions(seq: list) -> list:
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def _getArcsUtilizedIDs(arcBasedShortestPathsOriginalIDs: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    # obtain arc utilized
    arcsUtilizedWithRepetitions: list[tuple[int, int]] = [arc for path in arcBasedShortestPathsOriginalIDs for arc in
                                                          path]
    # call function which removes repetitions
    arcsUtilizedIDs: list[tuple[int, int]] = _removeRepetitions(arcsUtilizedWithRepetitions)
    return arcsUtilizedIDs


def _mapArcBasedShortestPaths(arcBasedShortestPathsOriginalIDs: list[list[tuple[int, int]]],
                              arcsUtilizedIDs: list[tuple[int, int]]):
    # map arcs in the order in which they appear in arc utilized without repetitions: mapping established
    arcBasedShortestPaths = [list(map(lambda arc: arcsUtilizedIDs.index(arc) + 1, arc)) for arc in
                             arcBasedShortestPathsOriginalIDs]  # + 1 makes the arcs ids starting from 1

    # add to each path a final dummy edge, representing the sink
    for path in arcBasedShortestPaths:
        path.append(0)

    return arcBasedShortestPaths


def _getTravelTimesArcsUtilized(manhattanGraph: DiGraph, arcsUtilizedIDs: list[tuple[int, int]]):
    travelTimesArcsUtilized = [manhattanGraph[origin][destination]["nominal_travel_time"]
                               for origin, destination in
                               arcsUtilizedIDs]
    travelTimesArcsUtilized.insert(0, 0)
    return travelTimesArcsUtilized


def _getNominalCapacityArcsUtilized(manhattanGraph: DiGraph, arcsUtilizedIDs: list[tuple[int, int]]):
    nominalCapacitiesArcsUtilized = [manhattanGraph[origin][destination]["nominal_capacity"] for
                                     origin, destination in arcsUtilizedIDs]
    nominalCapacitiesArcsUtilized.insert(0, 0)
    return nominalCapacitiesArcsUtilized


def _getOsmInfoArcs(manhattanGraph: DiGraph, arcsUtilizedIDs: list[tuple[int, int]]) -> \
        list[dict[str, int]]:
    osmInfoArcs = [
        {**manhattanGraph[origin][destination]}
        for origin, destination in arcsUtilizedIDs
    ]
    osmInfoArcs.insert(0, dict())
    return osmInfoArcs


ArcsFeatures = collections.namedtuple("ArcsFeatures", ["travelTimesArcsUtilized",
                                                       "nominalCapacitiesArcs",
                                                       "osmInfoArcsUtilized"])


def getArcBasedPathsWithFeatures(nodeBasedShortestPaths: list[list[int]],
                                 manhattanGraph: DiGraph) -> (
        list[list[int]], list[float], list[int], list[dict[str, typing.Any]]):
    arcBasedShortestPathsOriginalIDs = getArcBasedShortestPathsOriginalIDs(nodeBasedShortestPaths)
    arcsUtilizedIDs = _getArcsUtilizedIDs(arcBasedShortestPathsOriginalIDs)
    arcBasedShortestPaths = _mapArcBasedShortestPaths(arcBasedShortestPathsOriginalIDs, arcsUtilizedIDs)
    osmInfoArcs = _getOsmInfoArcs(manhattanGraph, arcsUtilizedIDs)
    travelTimesArcsUtilized = _getTravelTimesArcsUtilized(manhattanGraph, arcsUtilizedIDs)
    nominalCapacitiesArcs = _getNominalCapacityArcsUtilized(manhattanGraph, arcsUtilizedIDs)
    arcsFeatures = ArcsFeatures(travelTimesArcsUtilized=travelTimesArcsUtilized,
                                nominalCapacitiesArcs=nominalCapacitiesArcs,
                                osmInfoArcsUtilized=osmInfoArcs)
    return arcBasedShortestPaths, arcsFeatures
