import gurobipy as grb
import numpy as np
from gurobipy import Model
from input_data import CONSTR_TOLERANCE, USE_GUROBI_INDICATORS, TOLERANCE
from instance_module.instance import Instance
from utils.aliases import *


def _add_load_constraint(model: Model, vehicle: int, arc: int) -> None:
    """Add load constraints for a specific vehicle and arc."""
    model.addConstr(
        model._load[vehicle][arc] == grb.quicksum(
            model._gamma[arc][vehicle][other_vehicle]
            for other_vehicle in model._gamma[arc][vehicle]
        ) + 1,
        name=f"load_constraint_arc_{arc}_vehicle_{vehicle}"
    )


def _add_pwl_delay_constraint(model: Model, instance: Instance, vehicle: int, arc: int) -> None:
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

    model.addGenConstrPWL(
        model._load[vehicle][arc], model._delay[vehicle][arc],
        x_axis_values, y_axis_values,
        name=f"piecewise_delay_arc_{arc}_vehicle_{vehicle}"
    )


def _add_alpha_constraints(model: Model, arc: int, v1: int, v2: int) -> None:
    """Add alpha constraints for two vehicles on a given arc."""
    if isinstance(model._alpha[arc][v1][v2], grb.Var):
        model._numBigMConstraints += 2

        if USE_GUROBI_INDICATORS:
            model.addGenConstrIndicator(
                model._alpha[arc][v1][v2], True,
                model._departure[v1][arc] - model._departure[v2][arc] - CONSTR_TOLERANCE,
                grb.GRB.GREATER_EQUAL, 0,
                name=f"alpha_constr_one_arc_{arc}_vehicles_{v1}_{v2}"
            )
            model.addGenConstrIndicator(
                model._alpha[arc][v1][v2], False,
                model._departure[v1][arc] - model._departure[v2][arc] + CONSTR_TOLERANCE,
                grb.GRB.LESS_EQUAL, 0,
                name=f"alpha_constr_two_arc_{arc}_vehicles_{v1}_{v2}"
            )
        else:
            M1 = int(
                np.ceil(model._departure[v1][arc]._ub - model._departure[v2][arc]._lb + CONSTR_TOLERANCE + TOLERANCE))
            M2 = int(
                np.ceil(model._departure[v2][arc]._ub - model._departure[v1][arc]._lb + CONSTR_TOLERANCE + TOLERANCE))

            model.addConstr(
                model._departure[v1][arc] - model._departure[v2][arc] + CONSTR_TOLERANCE <= M1 * model._alpha[arc][v1][
                    v2],
                name=f"alpha_constr_one_arc_{arc}_vehicles_{v1}_{v2}"
            )
            model.addConstr(
                model._departure[v2][arc] - model._departure[v1][arc] + CONSTR_TOLERANCE <= M2 * (
                        1 - model._alpha[arc][v1][v2]),
                name=f"alpha_constr_two_arc_{arc}_vehicles_{v1}_{v2}"
            )


def _add_beta_constraints(model: Model, arc: int, first_vehicle: int, second_vehicle: int,
                          second_vehicle_path: list[int], arc_travel_time: float) -> None:
    """Add beta constraints for two vehicles on a specific arc."""
    if isinstance(model._beta[arc][first_vehicle][second_vehicle], grb.Var):
        # Get the index of the current arc and the next arc in the path of the second vehicle
        idx_second_vehicle_path = second_vehicle_path.index(arc)
        next_arc_second_vehicle = second_vehicle_path[idx_second_vehicle_path + 1]

        # Increment the count of Big-M constraints
        model._numBigMConstraints += 2

        if USE_GUROBI_INDICATORS:
            # Add indicator constraints
            model.addGenConstrIndicator(
                model._beta[arc][first_vehicle][second_vehicle], False,
                model._departure[second_vehicle][next_arc_second_vehicle] + CONSTR_TOLERANCE
                - model._departure[first_vehicle][arc],
                grb.GRB.LESS_EQUAL, 0,
                name=f"beta_to_zero_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
            )
            model.addGenConstrIndicator(
                model._beta[arc][first_vehicle][second_vehicle], True,
                model._departure[second_vehicle][next_arc_second_vehicle] - CONSTR_TOLERANCE
                - model._departure[first_vehicle][arc],
                grb.GRB.GREATER_EQUAL, 0,
                name=f"beta_to_one_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
            )
        else:
            # use BIG-M constraints
            M3 = int(np.ceil(
                model._departure[second_vehicle][next_arc_second_vehicle]._ub
                - model._departure[first_vehicle][arc]._lb + CONSTR_TOLERANCE + TOLERANCE
            ))
            M4 = int(np.ceil(model._departure[first_vehicle][arc]._ub - model._departure[second_vehicle][
                arc]._lb - arc_travel_time + CONSTR_TOLERANCE + TOLERANCE))

            # Add Big-M constraints
            model.addConstr(
                model._departure[second_vehicle][next_arc_second_vehicle]
                - model._departure[first_vehicle][arc] + CONSTR_TOLERANCE
                <= M3 * model._beta[arc][first_vehicle][second_vehicle],
                name=f"beta_to_zero_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
            )
            model.addConstr(
                model._departure[first_vehicle][arc]
                - model._departure[second_vehicle][next_arc_second_vehicle] + CONSTR_TOLERANCE
                <= M4 * (1 - model._beta[arc][first_vehicle][second_vehicle]),
                name=f"beta_to_one_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
            )


def _add_gamma_constraints(model: Model, arc: int, v1: int, v2: int) -> None:
    """Add gamma constraints for two vehicles on a given arc."""
    if isinstance(model._gamma[arc][v1][v2], grb.Var):
        model._numBigMConstraints += 2
        model.addConstr(
            model._gamma[arc][v1][v2] >= model._alpha[arc][v1][v2] + model._beta[arc][v1][v2] - 1,
            name=f"gamma_1_constr_arc_{arc}_vehicles_{v1}_{v2}"
        )
        model.addConstr(
            model._gamma[arc][v1][v2] <= (model._alpha[arc][v1][v2] + model._beta[arc][v1][v2]) / 2,
            name=f"gamma_2_constr_arc_{arc}_vehicles_{v1}_{v2}"
        )


def _add_conflict_constraints_between_vehicle_pair(
        model: Model,
        first_vehicle: int,
        second_vehicle: int,
        arc: int,
        second_vehicle_path: list[int],
        arc_travel_time: float
) -> None:
    """Add conflict constraints (alpha, beta, gamma) between two vehicles on a specific arc."""
    _add_alpha_constraints(model, arc, first_vehicle, second_vehicle)
    _add_beta_constraints(model, arc, first_vehicle, second_vehicle, second_vehicle_path, arc_travel_time)
    _add_gamma_constraints(model, arc, first_vehicle, second_vehicle)


def add_conflict_constraints(model: Model, instance: Instance) -> None:
    """Add conflict constraints to the model."""
    print("Adding conflict constraints...", end=" ")

    for arc in model._alpha:
        _add_constraints_for_arc(model, instance, arc)

    print("done!")
    print(f"Number of BigM constraints in model: {model._numBigMConstraints}")
    model.update()


def _add_constraints_for_arc(model: Model, instance: Instance, arc: int) -> None:
    """Add conflict constraints for a specific arc."""
    arc_travel_time = instance.travel_times_arcs[arc]

    for first_vehicle in model._alpha[arc]:
        if isinstance(model._load[first_vehicle][arc], grb.Var):
            _add_vehicle_constraints(model, instance, arc, first_vehicle, arc_travel_time)


def _add_vehicle_constraints(model: Model, instance: Instance, arc: int, first_vehicle: int,
                             arc_travel_time: float) -> None:
    """Add constraints for a specific vehicle on a given arc."""
    _add_load_constraint(model, first_vehicle, arc)
    _add_pwl_delay_constraint(model, instance, first_vehicle, arc)

    for second_vehicle in model._alpha[arc][first_vehicle]:
        if first_vehicle < second_vehicle:
            _add_pairwise_conflict_constraints(model, arc, first_vehicle, second_vehicle, instance, arc_travel_time)


def _add_pairwise_conflict_constraints(
        model: Model, arc: int, first_vehicle: int, second_vehicle: int, instance: Instance, arc_travel_time: float
) -> None:
    """Add conflict constraints between two vehicles on the same arc."""
    _add_conflict_constraints_between_vehicle_pair(
        model, first_vehicle, second_vehicle, arc, instance.trip_routes[second_vehicle], arc_travel_time
    )
    _add_conflict_constraints_between_vehicle_pair(
        model, second_vehicle, first_vehicle, arc, instance.trip_routes[first_vehicle], arc_travel_time
    )


def add_travel_continuity_constraints(model: Model, instance: Instance) -> None:
    """Add travel continuity constraints to the model."""
    print("Adding travel continuity constraints...")

    for vehicle in model._departure:
        for position in range(1, len(model._departure[vehicle])):
            current_arc = instance.trip_routes[vehicle][position]
            prev_arc = instance.trip_routes[vehicle][position - 1]

            model.addConstr(
                model._departure[vehicle][current_arc] - model._departure[vehicle][prev_arc] -
                model._delay[vehicle][prev_arc] == instance.travel_times_arcs[prev_arc],
                name=f"continuity_vehicle_{vehicle}_arc_{current_arc}"
            )


def add_objective_function(model: Model) -> None:
    """Set the objective function for minimizing total delay."""
    print("Setting the objective function...")
    model.addConstr(
        model._totalDelay == grb.quicksum(
            model._delay[vehicle][arc] for vehicle in model._delay for arc in model._delay[vehicle]
        ),
        name="total_delay_constraint"
    )
    model.setObjective(model._totalDelay, grb.GRB.MINIMIZE)
    print("Objective: Minimization of total delay.")
