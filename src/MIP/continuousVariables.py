import gurobipy as grb
from gurobipy import Model

from utils.classes import EpochSolution
from instanceModule.instance import Instance
from inputData import FIX_MODEL


def _addDepartureVariable(model: Model, vehicle: int, arc: int, instance: Instance, statusQuo: EpochSolution,
                          epochWarmStart) -> None:
    arcIndex = instance.trip_routes[vehicle].index(arc)
    earliestDepartureTime = instance.earliestDepartureTimes[vehicle][arcIndex]
    latestDepartureTime = instance.latestDepartureTimes[vehicle][arcIndex]
    departure = statusQuo.congestedSchedule[vehicle][arcIndex]
    if FIX_MODEL:
        fix_dep = epochWarmStart.congestedSchedule[vehicle][arcIndex]
        model._departure[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                      name=f"departure_vehicle_{str(vehicle)}_arc_{str(arc)}",
                                                      lb=fix_dep, ub=fix_dep)
    else:
        model._departure[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                      name=f"departure_vehicle_{str(vehicle)}_arc_{str(arc)}",
                                                      lb=earliestDepartureTime, ub=latestDepartureTime)
    model._departure[vehicle][arc]._lb = earliestDepartureTime
    model._departure[vehicle][arc]._ub = latestDepartureTime
    assert earliestDepartureTime - 1e-4 <= departure <= latestDepartureTime + 1e-6, f"earliest departure time: {earliestDepartureTime} <\=" \
                                                                                    f"departure: {departure} <\= " \
                                                                                    f"latest departure time: {latestDepartureTime}"


def _addDelayVariable(model: Model, vehicle: int, arc: int, instance: Instance) -> None:
    if vehicle in instance.conflictingSets[arc]:
        position = instance.trip_routes[vehicle].index(arc)
        lb = instance.minDelayOnArc[vehicle][position]
        ub = instance.maxDelayOnArc[vehicle][position]

        model._delay[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                  name=f"delay_vehicle_{str(vehicle)}_arc_{str(arc)}", lb=lb, ub=ub)

        model._delay[vehicle][arc]._lb = lb
        model._delay[vehicle][arc]._ub = ub
        assert lb <= ub + 1e-6
    else:
        model._delay[vehicle][arc] = 0


def _addLoadVariable(model: Model, vehicle: int, arc: int, conflictingSet: list[int]) -> None:
    if vehicle in conflictingSet:
        # ub = max load

        lb = sum(
            model._gamma[arc][vehicle][second_vehicle]._lb if isinstance(model._gamma[arc][vehicle][second_vehicle],
                                                                         grb.Var) else model._gamma[arc][vehicle][
                second_vehicle] for second_vehicle in model._gamma[arc][vehicle]) + 1

        ub = sum(
            model._gamma[arc][vehicle][second_vehicle]._ub if isinstance(model._gamma[arc][vehicle][second_vehicle],
                                                                         grb.Var) else model._gamma[arc][vehicle][
                second_vehicle] for second_vehicle in model._gamma[arc][vehicle]) + 1
        model._load[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                 name=f"load_vehicle_{vehicle}_arc_{arc}", lb=lb, ub=ub)
        assert lb <= ub
    else:
        model._load[vehicle][arc] = 1


def _addContinuousVariablesVehicleOnArc(model, instance, statusQuo, vehicle, arc, epochWarmStart) -> None:
    conflictingSet = instance.conflictingSets[arc]
    _addDepartureVariable(model, vehicle, arc, instance, statusQuo, epochWarmStart)
    _addDelayVariable(model, vehicle, arc, instance)
    _addLoadVariable(model, vehicle, arc, conflictingSet)


def addContinuousVariables(model: Model, instance: Instance, statusQuo: EpochSolution, epochWarmStart) -> None:
    # continuous variables
    print("Creating continuous variables... ", end="")
    model._totalDelay = model.addVar(vtype=grb.GRB.CONTINUOUS, name="total_delay")

    model._departure = {}
    model._delay = {}
    model._load = {}

    for vehicle, path in enumerate(instance.trip_routes):
        model._departure[vehicle] = {}
        model._delay[vehicle] = {}
        model._load[vehicle] = {}

        for position, arc in enumerate(path):
            _addContinuousVariablesVehicleOnArc(model, instance, statusQuo, vehicle, arc, epochWarmStart)

    print("done!")
