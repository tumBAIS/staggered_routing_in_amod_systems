import gurobipy as grb
from MIP import StaggeredRoutingModel
from input_data import USE_GUROBI_INDICATORS
from instance_module.instance import Instance


def get_x_and_y_points_pwl_function(instance: Instance, arc: int) -> \
        (list[float], list[float]):
    """Add piecewise linear (PWL) delay constraints."""
    x_axis_values, y_axis_values = [0], [0]
    prev_th, height_prev_piece, prev_slope = 0, 0, 0

    # Initialize variables for the last piece outside the loop
    th_capacity = 0
    piece_slope = 0

    for i, slope in enumerate(instance.input_data.list_of_slopes):
        th_capacity = instance.capacities_arcs[arc] * instance.input_data.list_of_thresholds[i]
        piece_slope = instance.travel_times_arcs[arc] * slope / instance.capacities_arcs[arc]

        if i == 0:
            x_axis_values.append(th_capacity)
            y_axis_values.append(0)
        else:
            pwl_at_th_cap = height_prev_piece + prev_slope * (th_capacity - prev_th)
            y_axis_values.append(pwl_at_th_cap)
            x_axis_values.append(th_capacity)

        prev_th, prev_slope, height_prev_piece = th_capacity, piece_slope, y_axis_values[-1]

    th_capacity += 1
    pwl_at_th_cap = height_prev_piece + piece_slope * (th_capacity - prev_th)
    x_axis_values.append(th_capacity)
    y_axis_values.append(pwl_at_th_cap)
    return x_axis_values, y_axis_values


def _add_conflict_constraints_between_vehicle_pair(
        model: StaggeredRoutingModel,
        first_vehicle: int,
        second_vehicle: int,
        arc: int,
        second_vehicle_path: list[int],
        arc_travel_time: float
) -> None:
    """Add conflict constraints (alpha, beta, gamma) between two vehicles on a specific arc."""

    if USE_GUROBI_INDICATORS:
        model.add_alpha_constraints_indicators(arc, first_vehicle, second_vehicle)
        model.add_beta_constraints_indicators(arc, first_vehicle, second_vehicle, second_vehicle_path)
    else:
        model.add_alpha_constraints(arc, first_vehicle, second_vehicle)
        model.add_beta_constraints(arc, first_vehicle, second_vehicle, second_vehicle_path, arc_travel_time)

    model.add_gamma_constraints(arc, first_vehicle, second_vehicle)


def add_conflict_constraints(model: StaggeredRoutingModel, instance: Instance) -> None:
    """Add conflict constraints to the model."""
    print("Adding conflict constraints...", end=" ")

    for arc in model._alpha:
        _add_constraints_for_arc(model, instance, arc)

    print("done!")
    print(f"Number of BigM constraints in model: {model._numBigMConstraints}")
    model.update()


def _add_constraints_for_arc(model: StaggeredRoutingModel, instance: Instance, arc: int) -> None:
    """Add conflict constraints for a specific arc."""
    arc_travel_time = instance.travel_times_arcs[arc]

    for first_vehicle in model._alpha[arc]:
        if isinstance(model._load[first_vehicle][arc], grb.Var):
            _add_vehicle_constraints(model, instance, arc, first_vehicle, arc_travel_time)


def _add_vehicle_constraints(model: StaggeredRoutingModel, instance: Instance, arc: int, trip: int,
                             arc_travel_time: float) -> None:
    """Add constraints for a specific vehicle on a given arc."""
    model.add_load_constraint(trip, arc)
    x_points, y_points = get_x_and_y_points_pwl_function(instance, arc)
    model.add_pwl_constraint(trip, arc, x_points, y_points)

    for conflicting_trip in model.get_conflicting_trips(arc, trip):
        if trip < conflicting_trip:
            _add_conflict_constraints_between_vehicle_pair(
                model, trip, conflicting_trip, arc, instance.trip_routes[conflicting_trip], arc_travel_time)
            _add_conflict_constraints_between_vehicle_pair(
                model, conflicting_trip, trip, arc, instance.trip_routes[trip], arc_travel_time)
