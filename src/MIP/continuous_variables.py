from utils.classes import Solution
from instance_module.instance import Instance
from input_data import FIX_MODEL, TOLERANCE
from MIP import StaggeredRoutingModel


def _add_departure_variable(
        model: StaggeredRoutingModel, vehicle: int, arc: int, instance: Instance, status_quo: Solution,
        epoch_warm_start: Solution
) -> None:
    """Add departure variable for a specific vehicle and arc."""
    arc_index = instance.trip_routes[vehicle].index(arc)
    earliest_departure = instance.earliest_departure_times[vehicle][arc_index]
    latest_departure = instance.latest_departure_times[vehicle][arc_index]
    departure = status_quo.congested_schedule[vehicle][arc_index]
    assert (
            earliest_departure - TOLERANCE <= departure <= latest_departure + TOLERANCE
    ), f"Invalid departure time for vehicle {vehicle} on arc {arc}, position {arc_index}: {earliest_departure - TOLERANCE} <\= {departure} <\= {latest_departure + TOLERANCE}"

    if FIX_MODEL:
        fixed_departure = epoch_warm_start.congested_schedule[vehicle][arc_index]
        model.add_continuous_var(vehicle, arc, fixed_departure, fixed_departure, "departure")

    else:
        model.add_continuous_var(vehicle, arc, earliest_departure, latest_departure, "departure")


def _add_delay_variable(model: StaggeredRoutingModel, vehicle: int, arc: int, instance: Instance) -> None:
    """Add delay variable for a specific vehicle and arc."""
    if vehicle in instance.conflicting_sets[arc]:
        position = instance.trip_routes[vehicle].index(arc)
        lb = instance.min_delay_on_arc[vehicle][position]
        ub = instance.max_delay_on_arc[vehicle][position]
        model.add_continuous_var(vehicle, arc, lb, ub, "delay")
    else:
        model.add_continuous_var(vehicle, arc, 0, 0, "delay", True)


def _add_load_variable(model: StaggeredRoutingModel, trip: int, arc: int, conflicting_set: list[int]) -> None:
    """Add load variable for a specific vehicle and arc."""
    if trip in conflicting_set:

        lb = (sum(model.get_conflict_pair_var_bound(
            bound="lb", var_name="gamma", arc=arc, first_trip=trip, second_trip=conflicting_trip) for conflicting_trip
                  in model.get_conflicting_trips(arc, trip)) + 1)

        ub = (sum(model.get_conflict_pair_var_bound(
            bound="ub", var_name="gamma", arc=arc, first_trip=trip, second_trip=conflicting_trip) for conflicting_trip
                  in model.get_conflicting_trips(arc, trip)) + 1)

        model.add_continuous_var(trip, arc, lb, ub, "load")

    else:
        model.add_continuous_var(trip, arc, 1, 1, "load", True)


def _add_continuous_variables_vehicle_on_arc(
        model: StaggeredRoutingModel, instance: Instance, status_quo: Solution, vehicle: int, arc: int,
        epoch_warm_start
) -> None:
    """Add all continuous variables (departure, delay, load) for a specific vehicle and arc."""
    conflicting_set = instance.conflicting_sets[arc]
    _add_departure_variable(model, vehicle, arc, instance, status_quo, epoch_warm_start)
    _add_delay_variable(model, vehicle, arc, instance)
    _add_load_variable(model, vehicle, arc, conflicting_set)


def add_continuous_variables(
        model: StaggeredRoutingModel, instance: Instance, status_quo: Solution, epoch_warm_start
) -> None:
    """Create all continuous variables for the optimization model."""
    print("Creating continuous variables... ", end="")

    for trip_id, path in enumerate(instance.trip_routes):
        for arc in path:
            _add_continuous_variables_vehicle_on_arc(model, instance, status_quo, trip_id, arc, epoch_warm_start)

    print("done!")
