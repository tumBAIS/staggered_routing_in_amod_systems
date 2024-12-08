import gurobipy as grb
from gurobipy import Model

from utils.classes import EpochSolution
from instance_module.instance import Instance
from input_data import FIX_MODEL


def _add_departure_variable(model: Model, vehicle: int, arc: int, instance: Instance, statusQuo: EpochSolution,
                            epochWarmStart) -> None:
    arcIndex = instance.trip_routes[vehicle].index(arc)
    earliestDepartureTime = instance.earliest_departure_times[vehicle][arcIndex]
    latestDepartureTime = instance.latest_departure_times[vehicle][arcIndex]
    departure = statusQuo.congested_schedule[vehicle][arcIndex]
    if FIX_MODEL:
        fix_dep = epochWarmStart.congested_schedule[vehicle][arcIndex]
        model._departure[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                      name=f"departure_vehicle_{str(vehicle)}_arc_{str(arc)}",
                                                      lb=fix_dep, ub=fix_dep)
    else:
        model._departure[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                      name=f"departure_vehicle_{str(vehicle)}_arc_{str(arc)}",
                                                      lb=earliestDepartureTime, ub=latestDepartureTime)
    model._departure[vehicle][arc]._lb = earliestDepartureTime
    model._departure[vehicle][arc]._ub = latestDepartureTime
    assert earliestDepartureTime - 1e-4 <= departure <= latestDepartureTime + 1e-6, rf"earliest departure time: {earliestDepartureTime} <\=" \
                                                                                    rf"departure: {departure} <\= " \
                                                                                    f"latest departure time: {latestDepartureTime}"


def _add_delay_variable(model: Model, vehicle: int, arc: int, instance: Instance) -> None:
    if vehicle in instance.conflicting_sets[arc]:
        position = instance.trip_routes[vehicle].index(arc)
        lb = instance.min_delay_on_arc[vehicle][position]
        ub = instance.max_delay_on_arc[vehicle][position]

        model._delay[vehicle][arc] = model.addVar(vtype=grb.GRB.CONTINUOUS,
                                                  name=f"delay_vehicle_{str(vehicle)}_arc_{str(arc)}", lb=lb, ub=ub)

        model._delay[vehicle][arc]._lb = lb
        model._delay[vehicle][arc]._ub = ub
        assert lb <= ub + 1e-6
    else:
        model._delay[vehicle][arc] = 0


def _add_load_variable(model: Model, vehicle: int, arc: int, conflictingSet: list[int]) -> None:
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


def _add_continuous_variables_vehicle_on_arc(model, instance, statusQuo, vehicle, arc, epochWarmStart) -> None:
    conflictingSet = instance.conflicting_sets[arc]
    _add_departure_variable(model, vehicle, arc, instance, statusQuo, epochWarmStart)
    _add_delay_variable(model, vehicle, arc, instance)
    _add_load_variable(model, vehicle, arc, conflictingSet)


def add_continuous_variables(model: Model, instance: Instance, statusQuo: EpochSolution, epochWarmStart) -> None:
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
            _add_continuous_variables_vehicle_on_arc(model, instance, statusQuo, vehicle, arc, epochWarmStart)

    print("done!")
