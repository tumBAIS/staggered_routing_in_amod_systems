from __future__ import annotations

from processing.shortcuts import addShortcuts
from instanceModule.graph import import_graph, reduceGraph, setArcsNominalTravelTimesAndCapacities
from instanceModule.instance import Instance, getInstance, printTotalFreeFlowTime
from instanceModule.paths import getNodeBasedShortestPaths, getArcBasedPathsWithFeatures
from instanceModule.rides import import_rides_df, getReleaseTimesAndArrivalTimesDataset
from inputData import InputData
from congestionModel.core import getDeadlines


def getNotSimplifiedInstance(inputData: InputData) -> Instance:
    taxiRides = import_rides_df(inputData)
    graph = import_graph(inputData)
    # nodeBasedShortestPaths = getNodeBasedShortestPaths(taxiRides, graph)
    # releaseTimes, arrivalTimes = getReleaseTimesAndArrivalTimesDataset(taxiRides)
    reduceGraph(graph, taxiRides["path"], inputData)
    nodeBasedShortestPaths = addShortcuts(inputData, graph, taxiRides, nodeBasedShortestPaths)
    setArcsNominalTravelTimesAndCapacities(graph, inputData)

    arcBasedShortestPaths, arcsFeatures = getArcBasedPathsWithFeatures(nodeBasedShortestPaths, graph)
    instance = getInstance(inputData, arcBasedShortestPaths, arcsFeatures, releaseTimes, arrivalTimes)

    printTotalFreeFlowTime(instance)
    deadlines = getDeadlines(instance)
    instance.set_deadlines(deadlines)
    instance.set_max_staggering_applicable()
    instance.check_optional_fields()
    return instance
