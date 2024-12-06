from __future__ import annotations

import datetime
import itertools

from MIP.support import saveSolutionInExternalFile
from congestionModel.core import getDelaysOnArcs, getStaggeringApplicable
from gurobipy import Model
from inputData import TOLERANCE, ACTIVATE_ASSERTIONS
from utils.classes import CompleteSolution, HeuristicSolution
from utils.aliases import VehicleSchedules
from instanceModule.instance import Instance
import gurobipy as grb
import cpp_module as cpp
from typing import Callable
from congestionModel.conflictBinaries import getConflictBinaries


def _getCurrentBounds(model: Model, startSolutionTime) -> None:
    lowerBoundImproved = model.cbGet(grb.GRB.Callback.MIP_OBJBND) >= model._lowerBound[-1]
    upperBoundImproved = model.cbGet(grb.GRB.Callback.MIP_OBJBST) <= model._upperBound[-1]

    if lowerBoundImproved and upperBoundImproved:
        # Update lower and upper bounds
        lowerBound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
        upperBound = model.cbGet(grb.GRB.Callback.MIP_OBJBST)
        model._lowerBound.append(lowerBound)
        model._upperBound.append(upperBound)

        # Calculate time spent in optimization
        timeSpentInOptimization = datetime.datetime.now().timestamp() - startSolutionTime
        model._optimizationTime.append(timeSpentInOptimization)

        # Calculate optimality gap if the upper bound is non-zero
        if upperBound > TOLERANCE:
            optimalityGap = (upperBound - lowerBound) / upperBound * 100
        else:
            optimalityGap = 0
        model._optimalityGap.append(optimalityGap)

    return


def _updateRemainingTimeForOptimization(model: Model, instance: Instance) -> None:
    totalOptimizationTime = instance.inputData.algorithm_time_limit
    elapsedTime = datetime.datetime.now().timestamp() - instance.startSolutionTime

    model._remainingTimeForOptimization = totalOptimizationTime - elapsedTime

    if model._remainingTimeForOptimization < 0:
        print("Terminating model from callback - Timelimit reached")
        model.terminate()

    return


def _getCallbackSolution(model: Model, instance: Instance, statusQuo: CompleteSolution) -> None:
    model._cbReleaseTimes = [model.cbGetSolution(model._departure[vehicle][path[0]])
                             for vehicle, path in enumerate(instance.trip_routes)]
    model._cbTotalDelay = sum(
        [sum(model.cbGetSolution(model._delay[vehicle][arc]) if isinstance(model._delay[vehicle][arc], grb.Var)
             else 0 for arc in model._delay[vehicle])
         for vehicle in (range(len(model._cbReleaseTimes)))])
    model._cbStaggeringApplied = [model._cbReleaseTimes[vehicle] - (statusQuo.congestedSchedule[vehicle][0]) for
                                  vehicle in range(len(model._cbReleaseTimes))]
    model._cbRemainingTimeSlack = getStaggeringApplicable(instance, model._cbStaggeringApplied)
    model._flagUpdate = True
    return


def _assertSchedule(model: Model, congestedSchedule: VehicleSchedules, delaysOnArcs: VehicleSchedules,
                    instance: Instance) -> None:
    if ACTIVATE_ASSERTIONS:
        for vehicle, (schedule, delays) in enumerate(zip(congestedSchedule, delaysOnArcs)):
            firstArc = instance.trip_routes[vehicle][0]

            # Assert the departure time of the first arc is within the maximum staggering limit
            assert schedule[0] - model._departure[vehicle][firstArc]._lb <= instance.maxStaggeringApplicable[
                vehicle] + 1e-6, \
                f"Invalid departure time for the first arc of vehicle {vehicle}"

            for position, arc in enumerate(instance.trip_routes[vehicle]):
                # Assert the departure time is within the lower and upper bounds
                assert model._departure[vehicle][arc]._lb - 1e-6 <= schedule[position] <= model._departure[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid departure time for arc {arc} of vehicle {vehicle} " \
                    f"({model._departure[vehicle][arc]._lb} <\= {schedule[position]} <\= {model._departure[vehicle][arc]._ub})"

                # Assert the delay is within the lower and upper bounds
                assert model._delay[vehicle][arc]._lb - 1e-6 <= delays[position] <= model._delay[vehicle][
                    arc]._ub + 1e-6, \
                    f"Invalid delay for arc {arc} of vehicle {vehicle}"


def _getHeuristicSolution(model: Model, instance: Instance) -> HeuristicSolution:
    model._flagUpdate = False
    cppParameters = [instance.inputData.algorithm_time_limit]
    instance.dueDates = instance.deadlines
    congestedSchedule = cpp.cppSchedulingLocalSearch(
        release_times=model._cbReleaseTimes,
        remaining_time_slack=model._cbRemainingTimeSlack,
        staggering_applied=model._cbStaggeringApplied,
        conflicting_sets=instance.conflictingSets,
        earliest_departure_times=instance.earliestDepartureTimes,
        latest_departure_times=instance.latestDepartureTimes,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        trip_routes=instance.trip_routes,
        deadlines=instance.deadlines,
        due_dates=instance.dueDates,
        list_of_slopes=instance.inputData.list_of_slopes,
        list_of_thresholds=instance.inputData.list_of_thresholds,
        parameters=cppParameters,
        lb_travel_time=instance.get_lb_travel_time()
    )

    delaysOnArcs = getDelaysOnArcs(instance, congestedSchedule)
    _assertSchedule(model, congestedSchedule, delaysOnArcs, instance)
    binaries = getConflictBinaries(instance.conflictingSets,
                                   instance.trip_routes,
                                   congestedSchedule)
    totalDelay = sum([sum(delaysOnArcVehicle) for delaysOnArcVehicle in delaysOnArcs])
    heuristicSolution = HeuristicSolution(congestedSchedule=congestedSchedule,
                                          delaysOnArcs=delaysOnArcs,
                                          binaries=binaries,
                                          totalDelay=totalDelay)

    return heuristicSolution


def _setHeuristicContinuousVariables(model, heuristicSolution):
    for vehicle in model._departure:
        for position, arc in enumerate(model._departure[vehicle]):
            model.cbSetSolution(model._departure[vehicle][arc],
                                heuristicSolution.congestedSchedule[vehicle][position])
            if isinstance(model._delay[vehicle][arc], grb.Var):
                model.cbSetSolution(model._delay[vehicle][arc], heuristicSolution.delaysOnArcs[vehicle][position])


def _setHeuristicBinaryVariables(model, heuristicSolution):
    for arc in model._gamma:
        for firstVehicle, secondVehicle in itertools.combinations(model._gamma[arc], 2):
            if heuristicSolution.binaries.gamma[arc][firstVehicle][secondVehicle] != -1:
                if isinstance(model._alpha[arc][firstVehicle][secondVehicle], grb.Var):
                    model.cbSetSolution(model._alpha[arc][firstVehicle][secondVehicle],
                                        heuristicSolution.binaries.alpha[arc][firstVehicle][secondVehicle])
                if isinstance(model._beta[arc][firstVehicle][secondVehicle], grb.Var):
                    model.cbSetSolution(model._beta[arc][firstVehicle][secondVehicle],
                                        heuristicSolution.binaries.beta[arc][firstVehicle][secondVehicle])
                if isinstance(model._gamma[arc][firstVehicle][secondVehicle], grb.Var):
                    model.cbSetSolution(model._gamma[arc][firstVehicle][secondVehicle],
                                        heuristicSolution.binaries.gamma[arc][firstVehicle][secondVehicle])
            if heuristicSolution.binaries.gamma[arc][secondVehicle][firstVehicle] != -1:
                if isinstance(model._alpha[arc][secondVehicle][firstVehicle], grb.Var):
                    model.cbSetSolution(model._alpha[arc][secondVehicle][firstVehicle],
                                        heuristicSolution.binaries.alpha[arc][secondVehicle][firstVehicle])
                if isinstance(model._beta[arc][secondVehicle][firstVehicle], grb.Var):
                    model.cbSetSolution(model._beta[arc][secondVehicle][firstVehicle],
                                        heuristicSolution.binaries.beta[arc][secondVehicle][firstVehicle])
                if isinstance(model._gamma[arc][secondVehicle][firstVehicle], grb.Var):
                    model.cbSetSolution(model._gamma[arc][secondVehicle][firstVehicle],
                                        heuristicSolution.binaries.gamma[arc][secondVehicle][firstVehicle])


def _suspendProcedure(heuristicSolution, model, instance) -> None:
    saveSolutionInExternalFile(heuristicSolution, instance)
    if model.cbGet(grb.GRB.Callback.MIP_OBJBND) > model._bestLowerBound:
        model._bestLowerBound = model.cbGet(grb.GRB.Callback.MIP_OBJBND)
    model.terminate()
    return


def _setHeuristicSolution(model: Model, heuristicSolution: HeuristicSolution, instance: Instance) -> None:
    solutionIsImproving: bool = model._cbTotalDelay - heuristicSolution.totalDelay > TOLERANCE
    if solutionIsImproving:
        print("setting heuristic solution in callback...", end=" ")
        _setHeuristicBinaryVariables(model, heuristicSolution)
        _setHeuristicContinuousVariables(model, heuristicSolution)
        returnValUseSolution = model.cbUseSolution()
        print(f"model.cbUseSolution() produced a solution with value {returnValUseSolution}")
        model.update()
        if returnValUseSolution == 1e+100:
            print("Heuristic solution has not been accepted - terminating MIP model")
            _suspendProcedure(heuristicSolution, model, instance)
    return


def callback(instance: Instance, statusQuo: CompleteSolution) -> Callable:
    def callLocalSearch(model, where) -> None:
        if where == grb.GRB.Callback.MIP:
            _getCurrentBounds(model, instance.startSolutionTime)
            _updateRemainingTimeForOptimization(model, instance)

        # Callback when MIP solutions are found
        if where == grb.GRB.Callback.MIPSOL:
            # Get the solution from the callback and update relevant variables
            _getCallbackSolution(model, instance, statusQuo)
            model._improvementClock = datetime.datetime.now().timestamp()
            model._bestUpperBound = model._cbTotalDelay

        # Callback when exploring MIP nodes
        if where == grb.GRB.Callback.MIPNODE:
            # Apply heuristic solution at the root node
            if model._flagUpdate:
                heuristicSolution = _getHeuristicSolution(model, instance)
                _setHeuristicSolution(model, heuristicSolution, instance)

    return callLocalSearch
