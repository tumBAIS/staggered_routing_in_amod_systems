from __future__ import annotations

import json
import os
import sys
import pickle
import typing
from dataclasses import dataclass

import shapely

from instanceModule.instance import Instance
from utils.classes import CompleteSolution, OptimizationMeasures


def linestring_to_dict(linestring):
    """
    Transform a LineString into a dictionary format.

    Args:
        linestring (LineString): The LineString object to transform.

    Returns:
        dict: A dictionary representing the LineString.
    """
    if not isinstance(linestring, shapely.LineString):
        return linestring

    # Extract the type and coordinates from the LineString
    geom_dict = {
        "type": "LineString",
        "coordinates": list(linestring.coords)
    }

    return geom_dict


def saveExperiment(inputSource: str, instance: Instance, statusQuo: CompleteSolution, solution: CompleteSolution):
    path_to_results = instance.inputData.path_to_results
    # Create a Pandas DataFrame with data from different classes
    inputData_to_save = instance.inputData.__dict__
    for arc, _ in enumerate(instance.osmInfoArcsUtilized):
        if arc > 0:
            instance.osmInfoArcsUtilized[arc] = linestring_to_dict(
                instance.osmInfoArcsUtilized[arc]["geometry"])
    statusQuo.binaries = {}
    solution.binaries = {}

    for i in range(len(statusQuo.congestedSchedule)):
        instance.maxStaggeringApplicable[i] = round(instance.maxStaggeringApplicable[i], 2)
        instance.deadlines[i] = round(instance.deadlines[i], 2)
        statusQuo.releaseTimes[i] = round(statusQuo.releaseTimes[i], 2)
        statusQuo.staggeringApplicable[i] = round(statusQuo.staggeringApplicable[i], 2)
        statusQuo.staggeringApplied[i] = round(statusQuo.staggeringApplied[i], 2)
        solution.releaseTimes[i] = round(solution.releaseTimes[i], 2)
        solution.staggeringApplicable[i] = round(solution.staggeringApplicable[i], 2)
        solution.staggeringApplied[i] = round(solution.staggeringApplied[i], 2)

        for j in range(len(statusQuo.congestedSchedule[i])):
            statusQuo.congestedSchedule[i][j] = round(statusQuo.congestedSchedule[i][j], 2)
            statusQuo.freeFlowSchedule[i][j] = round(statusQuo.freeFlowSchedule[i][j], 2)
            statusQuo.delaysOnArcs[i][j] = round(statusQuo.delaysOnArcs[i][j], 2)
            solution.congestedSchedule[i][j] = round(solution.congestedSchedule[i][j], 2)
            solution.freeFlowSchedule[i][j] = round(solution.freeFlowSchedule[i][j], 2)
            solution.delaysOnArcs[i][j] = round(solution.delaysOnArcs[i][j], 2)

    instance_data_to_save = instance.__dict__
    cols_to_delete = ["inputData", "nominalCapacitiesArcs", "releaseTimesDataset", "arrivalTimesDataset",
                      "undividedConflictingSets", "latestDepartureTimes", "earliestDepartureTimes", "minDelayOnArc",
                      "maxDelayOnArc", ]
    for col in cols_to_delete:
        del instance_data_to_save[col]
    for i in range(len(instance_data_to_save["travelTimesArcsUtilized"])):
        instance_data_to_save["travelTimesArcsUtilized"][i] = \
            round(instance_data_to_save["travelTimesArcsUtilized"][i], 2)

    output_data = {
        "input_data": inputData_to_save,
        'instance': instance_data_to_save,
        'statusQuo': statusQuo.__dict__,
        'solution': solution.__dict__,
    }

    with open(fr"{path_to_results}/results.json", 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=3)

    # save twice on cluster
    if inputSource == "console":
        pathToResults = sys.argv[2]
        with open(f'{pathToResults}/results.p', 'wb') as picklefile:
            pickle.dump(output_data, picklefile)

    return


@dataclass
class InitialOutputData:
    instance: Instance
    statusQuo: CompleteSolution
    warmStart: CompleteSolution

    def save_output(self, machine: str) -> None:
        if machine == "local":
            path_to_data = os.path.join(os.path.dirname(__file__), "../../results")
        else:
            path_to_data = sys.argv[2]
        with open(f"{path_to_data}/instance_file.p", "wb") as outfile:
            pickle.dump(self, outfile)
        return


@dataclass
class FinalOutputData:
    instance: Instance
    statusQuo: CompleteSolution
    warmStart: CompleteSolution
    modelSolution: CompleteSolution
    optimizationMeasures: OptimizationMeasures
    randomSolution: CompleteSolution
    mappedSystem: typing.Any

    def save_output(self, machine: str) -> None:
        if machine == "local":
            path_to_data = os.path.join(os.path.dirname(__file__), "../../results")
        else:
            path_to_data = sys.argv[2]
        with open(f"{path_to_data}/final_experimental_results.p", "wb") as outfile:
            pickle.dump(self, outfile)
        return
