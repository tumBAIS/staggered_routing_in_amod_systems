import datetime

import pandas as pd

from instanceModule.epochInstance import EpochInstances
from utils.classes import CompleteSolution


def printInfoArcsUtilized(instance):
    lengthArcs = _calculateLengthArcsUtilized(instance)
    dataframeInfo = _createInfoDataFrame(instance, lengthArcs)
    _printArcsUtilizedInfo(dataframeInfo)


def printInfoConflictingSetsSizes(instance):
    """ Prints information about sizes of conflicting sets and related statistics. """

    conflictingSetsSizes = [len(x) for x in instance.conflictingSets if x != []]
    confSetSeries = pd.Series(conflictingSetsSizes)

    print("#" * 44)
    print("### Distributional info conflicting sets ###")
    print("#" * 44, "\n")

    print(confSetSeries.describe())

    arcWithLargestConflictingSet = max(
        [arc for arc, time in enumerate(instance.travel_times_arcs)],
        key=lambda x: len(instance.conflictingSets[x])
    )

    print("Info arc with largest conflicting set:")
    print(f"Arc {arcWithLargestConflictingSet} info:")
    print(f"Conflicting set size: {len(instance.conflictingSets[arcWithLargestConflictingSet])}")
    print(f"Free flow travel time: {instance.travel_times_arcs[arcWithLargestConflictingSet]}")
    print(f"Nominal capacity: {instance.capacities_arcs[arcWithLargestConflictingSet]}")

    print("\nInfo outliers (points greater than 75th percentile + 1.5 * IQR):")
    Q1 = confSetSeries.quantile(0.25)
    Q3 = confSetSeries.quantile(0.75)
    IQR = Q3 - Q1
    outlierFilter = (confSetSeries >= Q3 + 1.5 * IQR)
    outliers = confSetSeries[outlierFilter]
    print(outliers.describe())
    print("#" * 44, "\n")


def printInfoLengthTrips(instance, congestedSchedule, freeFlowSchedule, delaysOnArcs):
    """
    Prints information about trip lengths, delays on arcs, and deadlines.
    """

    lengthTripsDF = _create_length_trips_dataframe(congestedSchedule, freeFlowSchedule)
    lengthTripsDFOnlYCongestedTrips = lengthTripsDF[lengthTripsDF['timeDifference'] > 1e-6]
    pd.options.display.float_format = '{:.6f}'.format
    _print_length_all_trips_info(lengthTripsDF)
    _print_length_congested_trips_info(lengthTripsDFOnlYCongestedTrips)
    _print_delays_on_arcs_info(instance, delaysOnArcs)


def _calculate_trip_lengths_in_minutes(schedule):
    return [(schedule[vehicle][-1] - schedule[vehicle][0]) / 60 for vehicle in range(len(schedule))]


def _calculate_time_differences(lengthCongestedTrips, lengthFFTrips):
    return [(lengthCongestedTrips[i] - lengthFFTrips[i]) for i in range(len(lengthFFTrips))]


def _create_length_trips_dataframe(congestedSchedule, freeFlowSchedule):
    lengthCongestedTrips = _calculate_trip_lengths_in_minutes(congestedSchedule)
    lengthFFTrips = _calculate_trip_lengths_in_minutes(freeFlowSchedule)
    timeDifference = _calculate_time_differences(lengthCongestedTrips, lengthFFTrips)
    lengthTripsDF = pd.DataFrame([lengthCongestedTrips, lengthFFTrips, timeDifference]).T
    lengthTripsDF.columns = ["congested", "freeFlow", "timeDifference"]
    return lengthTripsDF


def _get_delays_on_arcs_in_minutes_series(instance, delaysOnArcs):
    delaysOnArcsInMins = []
    delaysOnArcsInPerc = []
    travelTimeArcsOnWhichDelayOccur = []

    for vehicle, delays in enumerate(delaysOnArcs):
        for position, delay in enumerate(delays):
            if delay > 1e-5:
                arc = instance.trip_routes[vehicle][position]
                travel_time = instance.travel_times_arcs[arc]
                delay_in_sec = delay
                delay_percentage = (delay / travel_time) * 100

                delaysOnArcsInMins.append(delay_in_sec / 60)
                delaysOnArcsInPerc.append(delay_percentage)
                travelTimeArcsOnWhichDelayOccur.append(travel_time / 60)

    # Create a DataFrame
    data = {
        'Nominal travel time arc [min]': travelTimeArcsOnWhichDelayOccur,
        'Delay on arcs [min]': delaysOnArcsInMins,
    }
    return pd.DataFrame(data)


def _print_length_all_trips_info(lengthTripsDF):
    print("#" * 27)
    print("## Info length ALL trips [minutes] ##")
    print("#" * 27)
    print(lengthTripsDF.describe())
    print("#" * 27, "\n")


def _print_length_congested_trips_info(lengthTripsDF):
    print("#" * 27)
    print("## Info length ONLY CONGESTED trips [minutes] ##")
    print("#" * 27)
    print(lengthTripsDF.describe().round(2))
    print("#" * 27, "\n")


def _print_delays_on_arcs_info(instance, delaysOnArcs: list[list[int]]) -> None:
    delaysOnArcsSeries = _get_delays_on_arcs_in_minutes_series(instance, delaysOnArcs)
    print("#" * 31)
    print("## Info delays on arcs [minutes] ##")
    print("#" * 31)
    print(delaysOnArcsSeries.describe().round(2))
    print("#" * 31, "\n")


def _calculateLengthArcsUtilized(instance):
    return [travelTime * instance.inputData.speed / 3.6 for travelTime in instance.travel_times_arcs]


def _createInfoDataFrame(instance, lengthArcs):
    data = {
        "length [m]": lengthArcs,
        "travel times [min]": [x / 60 for x in instance.travel_times_arcs],
        "nominal capacities": instance.capacities_arcs
    }
    return pd.DataFrame(data)


def _printArcsUtilizedInfo(dataframeInfo):
    print("#" * 45)
    print("############ Info arcs utilized ############")
    print("#" * 45)
    print(dataframeInfo[1:].describe().round(2))
    print("#" * 45)


def print_insights_algorithm(
        completeStatusQuo: CompleteSolution,
        reconstructedSolution: CompleteSolution,
        epochInstances: EpochInstances):
    print("#" * 20)
    print("FINAL INSIGHTS ALGORITHM")
    print("#" * 20)
    print(f"Total delay complete status quo: {completeStatusQuo.totalDelay / 60:.2f} [min]")
    print(f"Total delay final solution: {reconstructedSolution.totalDelay / 60:.2f} [min]")
    delayReduction = (completeStatusQuo.totalDelay - reconstructedSolution.totalDelay) / \
                     completeStatusQuo.totalDelay if completeStatusQuo.totalDelay > 1e-6 else 0
    print(f"Total delay reduction: {delayReduction:.2%}")
    print(f"Total runtime algorithm: {datetime.datetime.now().timestamp() - epochInstances[0].clockStartEpoch:.2f} [s]")
