import gurobipy as grb
from gurobipy import Model
from utils.classes import EpochSolution
from instance_module.instance import Instance
from input_data import FIX_MODEL
from MIP import StaggeredRoutingModel


def _add_departure_variable(
        model: StaggeredRoutingModel, vehicle: int, arc: int, instance: Instance, status_quo: EpochSolution,
        epoch_warm_start
) -> None:
    """Add departure variable for a specific vehicle and arc."""
    arc_index = instance.trip_routes[vehicle].index(arc)
    earliest_departure = instance.earliest_departure_times[vehicle][arc_index]
    latest_departure = instance.latest_departure_times[vehicle][arc_index]
    departure = status_quo.congested_schedule[vehicle][arc_index]

    if FIX_MODEL:
        fixed_departure = epoch_warm_start.congested_schedule[vehicle][arc_index]
        model.add_departure_var(vehicle, arc, fixed_departure, fixed_departure)

    else:
        model.add_departure_var(vehicle, arc, earliest_departure, latest_departure)

    assert (
            earliest_departure - 1e-4 <= departure <= latest_departure + 1e-6
    ), f"Invalid departure time for vehicle {vehicle} on arc {arc}: {earliest_departure} <= {departure} <= {latest_departure}"


def _add_delay_variable(model: Model, vehicle: int, arc: int, instance: Instance) -> None:
    """Add delay variable for a specific vehicle and arc."""
    if vehicle in instance.conflicting_sets[arc]:
        position = instance.trip_routes[vehicle].index(arc)
        lb = instance.min_delay_on_arc[vehicle][position]
        ub = instance.max_delay_on_arc[vehicle][position]

        model._delay[vehicle][arc] = model.addVar(
            vtype=grb.GRB.CONTINUOUS, name=f"delay_vehicle_{vehicle}_arc_{arc}", lb=lb, ub=ub
        )

        model._delay[vehicle][arc]._lb = lb
        model._delay[vehicle][arc]._ub = ub

        assert lb <= ub + 1e-6, f"Invalid delay bounds for vehicle {vehicle} on arc {arc}: {lb} <= {ub}"
    else:
        model._delay[vehicle][arc] = 0


def _add_load_variable(model: Model, vehicle: int, arc: int, conflicting_set: list[int]) -> None:
    """Add load variable for a specific vehicle and arc."""
    if vehicle in conflicting_set:
        lb = sum(
            model._gamma[arc][vehicle][second_vehicle]._lb
            if isinstance(model._gamma[arc][vehicle][second_vehicle], grb.Var)
            else model._gamma[arc][vehicle][second_vehicle]
            for second_vehicle in model._gamma[arc][vehicle]
        ) + 1

        ub = sum(
            model._gamma[arc][vehicle][second_vehicle]._ub
            if isinstance(model._gamma[arc][vehicle][second_vehicle], grb.Var)
            else model._gamma[arc][vehicle][second_vehicle]
            for second_vehicle in model._gamma[arc][vehicle]
        ) + 1

        model._load[vehicle][arc] = model.addVar(
            vtype=grb.GRB.CONTINUOUS, name=f"load_vehicle_{vehicle}_arc_{arc}", lb=lb, ub=ub
        )

        assert lb <= ub, f"Invalid load bounds for vehicle {vehicle} on arc {arc}: {lb} <= {ub}"
    else:
        model._load[vehicle][arc] = 1


def _add_continuous_variables_vehicle_on_arc(
        model: Model, instance: Instance, status_quo: EpochSolution, vehicle: int, arc: int, epoch_warm_start
) -> None:
    """Add all continuous variables (departure, delay, load) for a specific vehicle and arc."""
    conflicting_set = instance.conflicting_sets[arc]
    _add_departure_variable(model, vehicle, arc, instance, status_quo, epoch_warm_start)
    _add_delay_variable(model, vehicle, arc, instance)
    _add_load_variable(model, vehicle, arc, conflicting_set)


def add_continuous_variables(
        model: StaggeredRoutingModel, instance: Instance, status_quo: EpochSolution, epoch_warm_start
) -> None:
    """Create all continuous variables for the optimization model."""
    print("Creating continuous variables... ", end="")

    for trip_id, path in enumerate(instance.trip_routes):
        model.add_trip_continuous_variables(trip_id)
        for arc in path:
            _add_continuous_variables_vehicle_on_arc(model, instance, status_quo, trip_id, arc, epoch_warm_start)

    print("done!")
