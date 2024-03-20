import itertools

import gurobipy as grb
import numpy as np
from gurobipy import Model
import math

from inputData import CONSTR_TOLERANCE, USE_GUROBI_INDICATORS, TOLERANCE
from instanceModule.instance import Instance
from inputData import MIN_SET_CAPACITY
from utils.aliases import *


def _addLoadConstraint(model, vehicle, arc):
    model.addConstr(model._load[vehicle][arc] == grb.quicksum(
        model._gamma[arc][vehicle][other_vehicles_utilizing_road]
        for other_vehicles_utilizing_road in
        model._gamma[arc][vehicle]) + 1, name=f"load_constraint_arc_{arc}_vehicle_{vehicle}")


def _check_third_piece_can_be_active(instance: Instance, arc: ArcID) -> bool:
    nominalCapacityArc = instance.nominalCapacitiesArcs[arc]
    return len(
        instance.conflictingSets[arc]) > nominalCapacityArc * instance.inputData.list_of_thresholds[0]


def _add_piecewise_linear_delay(model: Model, vehicle: VehicleID, arc: ArcID, first_capacity: float,
                                slope_second: float) -> None:
    x_axis_values = [0, first_capacity, first_capacity + 1, first_capacity + 2]
    y_axis_values = [0, 0, slope_second, 2 * slope_second]
    model.addGenConstrPWL(model._load[vehicle][arc], model._delay[vehicle][arc],
                          x_axis_values, y_axis_values, name=f"two_pieces_delay_arc_{arc}_vehicle_{vehicle}")


def _addPWLDelayConstraint(model: Model, instance: Instance, vehicle: int, arc: ArcID) -> None:
    # Initialize x-axis (vehicles count) and y-axis (delay) for the PWL function
    x_axis_values, y_axis_values = [0], [0]

    # Initialize PWL construction
    prev_th = 0
    height_prev_piece = 0
    th_capacity = 0
    slope = 0
    prev_slope = 0

    # Iterate through slopes to build the PWL points
    for i, slope in enumerate(instance.inputData.list_of_slopes):
        th_capacity = instance.nominalCapacitiesArcs[arc] * instance.inputData.list_of_thresholds[i]
        piece_slope = instance.travelTimesArcsUtilized[arc] * slope / instance.nominalCapacitiesArcs[arc]

        # Special handling for the first piece
        if i == 0:
            x_axis_values.append(th_capacity)
            y_axis_values.append(0)  # No delay for the capacity threshold
        else:
            pwl_at_th_cap = height_prev_piece + prev_slope * (th_capacity - prev_th)
            y_axis_values.append(pwl_at_th_cap)

            # Update for next iteration
            x_axis_values.append(th_capacity)
        prev_th = th_capacity
        prev_slope = piece_slope
        height_prev_piece = y_axis_values[-1]

    # Add one more point beyond the last threshold to extend the PWL function
    th_capacity += 1  # Increment to go beyond the last threshold
    piece_slope = instance.travelTimesArcsUtilized[arc] * slope / instance.nominalCapacitiesArcs[arc]
    pwl_at_th_cap = height_prev_piece + piece_slope * (th_capacity - prev_th)
    x_axis_values.append(th_capacity)
    y_axis_values.append(pwl_at_th_cap)

    # Add the PWL constraint to the model
    model.addGenConstrPWL(model._load[vehicle][arc], model._delay[vehicle][arc],
                          x_axis_values, y_axis_values,
                          name=f"piecewise_delay_arc_{arc}_vehicle_{vehicle}")


def _addAlphaConstraints(model: Model, arc: int, firstVehicle: int, secondVehicle: int) -> None:
    if isinstance(model._alpha[arc][firstVehicle][secondVehicle], grb.Var):
        model._numBigMConstraints += 2
        if USE_GUROBI_INDICATORS:
            model.addGenConstrIndicator(model._alpha[arc][firstVehicle][secondVehicle], True,
                                        model._departure[firstVehicle][arc] -
                                        model._departure[secondVehicle][arc] - CONSTR_TOLERANCE,
                                        grb.GRB.GREATER_EQUAL, 0,
                                        name=f"alpha_constr_one_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
            model.addGenConstrIndicator(model._alpha[arc][firstVehicle][secondVehicle], False,
                                        model._departure[firstVehicle][arc] -
                                        model._departure[secondVehicle][arc] + CONSTR_TOLERANCE,
                                        grb.GRB.LESS_EQUAL, 0,
                                        name=f"alpha_constr_two_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
        else:
            # using BIG-M constraints
            M1 = int(np.ceil(model._departure[firstVehicle][arc]._ub - model._departure[secondVehicle][
                arc]._lb + CONSTR_TOLERANCE + TOLERANCE))
            model.addConstr(
                model._departure[firstVehicle][arc] - model._departure[secondVehicle][arc] + CONSTR_TOLERANCE <= M1 *
                model._alpha[arc][firstVehicle][secondVehicle],
                name=f"alpha_constr_one_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
            M2 = int(np.ceil(model._departure[secondVehicle][arc]._ub - model._departure[firstVehicle][
                arc]._lb + CONSTR_TOLERANCE + TOLERANCE))
            model.addConstr(
                model._departure[secondVehicle][arc] - model._departure[firstVehicle][arc] + CONSTR_TOLERANCE <= M2 *
                (1 - model._alpha[arc][firstVehicle][secondVehicle]),
                name=f"alpha_constr_two_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")


def _addBetaConstraints(model: Model, arc: int, firstVehicle: int, secondVehicle: int,
                        secondVehiclePath: list[int], arc_travel_time: float) -> None:
    if isinstance(model._beta[arc][firstVehicle][secondVehicle], grb.Var):
        indexArcSecondVehiclePath = secondVehiclePath.index(arc)
        nextArcSecond = secondVehiclePath[indexArcSecondVehiclePath + 1]
        model._numBigMConstraints += 2
        if USE_GUROBI_INDICATORS:
            model.addGenConstrIndicator(model._beta[arc][firstVehicle][secondVehicle], False,
                                        model._departure[secondVehicle][
                                            nextArcSecond] + CONSTR_TOLERANCE
                                        - model._departure[firstVehicle][arc],
                                        grb.GRB.LESS_EQUAL, 0,
                                        name=f"beta_to_zero_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
            model.addGenConstrIndicator(model._beta[arc][firstVehicle][secondVehicle], True,
                                        model._departure[secondVehicle][
                                            nextArcSecond] - CONSTR_TOLERANCE
                                        - model._departure[firstVehicle][arc],
                                        grb.GRB.GREATER_EQUAL, 0,
                                        name=f"beta_to_one_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
        else:
            # use BIG-M constraints
            M3 = int(np.ceil(model._departure[secondVehicle][nextArcSecond]._ub - model._departure[firstVehicle][
                arc]._lb + CONSTR_TOLERANCE + TOLERANCE))
            model.addConstr(model._departure[secondVehicle][nextArcSecond] - model._departure[firstVehicle][
                arc] + CONSTR_TOLERANCE <=
                            M3 * model._beta[arc][firstVehicle][secondVehicle],
                            name=f"beta_to_zero_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
            M4 = int(np.ceil(model._departure[firstVehicle][arc]._ub - model._departure[secondVehicle][
                arc]._lb - arc_travel_time + CONSTR_TOLERANCE + TOLERANCE))
            model.addConstr(model._departure[firstVehicle][arc] - model._departure[secondVehicle][
                nextArcSecond] + CONSTR_TOLERANCE <=
                            M4 * (1 - model._beta[arc][firstVehicle][secondVehicle]),
                            name=f"beta_to_one_{arc}_vehicles_{firstVehicle}_{secondVehicle}")


def _addGammaConstraints(model: Model, arc: int, firstVehicle: int, secondVehicle: int) -> None:
    if isinstance(model._gamma[arc][firstVehicle][secondVehicle], grb.Var):
        model._numBigMConstraints += 2
        model.addConstr(model._gamma[arc][firstVehicle][secondVehicle] >=
                        model._alpha[arc][firstVehicle][secondVehicle] +
                        model._beta[arc][firstVehicle][secondVehicle] - 1,
                        name=f"gamma_1_constr_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")
        model.addConstr(model._gamma[arc][firstVehicle][secondVehicle] <=
                        (model._alpha[arc][firstVehicle][secondVehicle]
                         + model._beta[arc][firstVehicle][secondVehicle]) / 2,
                        name=f"gamma_2_constr_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")


def _addConflictConstraintsBetweenVehiclePair(model, firstVehicle, secondVehicle, arc, secondVehiclePath,
                                              arc_travel_time):
    _addAlphaConstraints(model, arc, firstVehicle, secondVehicle)
    _addBetaConstraints(model, arc, firstVehicle, secondVehicle, secondVehiclePath, arc_travel_time)
    _addGammaConstraints(model, arc, firstVehicle, secondVehicle)


def _addConstraintOnMaxSumAlphas(model: Model, arc: int, conflictingSetOnArc) -> None:
    # Create a constraint on the maximum sum of alpha variables for the given arc
    model.addConstr(
        grb.quicksum(
            model._alpha[arc][firstVehicle][secondVehicle]  # Sum of alpha variables for all vehicle pairs
            for firstVehicle in model._alpha[arc]
            for secondVehicle in model._alpha[arc][firstVehicle]
        ) == len(list(itertools.combinations(conflictingSetOnArc, 2))),  # Number of pairs in the conflicting set
        name=f"max_sum_alpha_arc_{arc}"
    )


def _addSumAlphasConstraint(model: Model, firstVehicle: int, secondVehicle: int, arc: int) -> None:
    model.addConstr(model._alpha[arc][firstVehicle][secondVehicle] + model._alpha[arc][secondVehicle][
        firstVehicle] == 1, name=f"sum_alphas_arc_{arc}_vehicles_{firstVehicle}_{secondVehicle}")


def addConflictConstraints(model: Model, instance: Instance) -> None:
    print("Adding conflict constraints...", end=" ")

    for arc in model._alpha:
        # Add constraint on the maximum sum of alpha variables for the current arc
        # _addConstraintOnMaxSumAlphas(model, arc, instance.conflictingSets[arc])
        arc_travel_time = instance.travelTimesArcsUtilized[arc]
        for firstVehicle in model._alpha[arc]:
            if isinstance(model._load[firstVehicle][arc], grb.Var):
                # Add load constraint and piecewise linear delay constraint for the first vehicle on the current arc
                _addLoadConstraint(model, firstVehicle, arc)
                _addPWLDelayConstraint(model, instance, firstVehicle, arc)

                for secondVehicle in model._alpha[arc][firstVehicle]:
                    if firstVehicle < secondVehicle:
                        # Add conflict constraints between the first and second vehicles on the current arc
                        _addConflictConstraintsBetweenVehiclePair(model, firstVehicle, secondVehicle, arc,
                                                                  instance.arcBasedShortestPaths[secondVehicle],
                                                                  arc_travel_time)
                        _addConflictConstraintsBetweenVehiclePair(model, secondVehicle, firstVehicle, arc,
                                                                  instance.arcBasedShortestPaths[firstVehicle],
                                                                  arc_travel_time)
                        # Add constraint on the sum of alpha variables for the first and second vehicles on the current arc
                        # _addSumAlphasConstraint(model, firstVehicle, secondVehicle, arc)
    print("done!")
    print(f"number of BigM constraints in model: {model._numBigMConstraints}")
    model.update()
    return


def addTravelContinuityConstraints(model: Model, instance: Instance) -> None:
    print("Writing the continuity constraints")
    for vehicle in model._departure:
        for position in range(1, len(model._departure[vehicle])):
            # Get the current and previous arcs for the vehicle at the given position
            currentArc = instance.arcBasedShortestPaths[vehicle][position]
            previousArc = instance.arcBasedShortestPaths[vehicle][position - 1]

            # Add the continuity constraint for the vehicle and arcs
            model.addConstr(
                model._departure[vehicle][currentArc] - model._departure[vehicle][previousArc] -
                model._delay[vehicle][previousArc] == instance.travelTimesArcsUtilized[previousArc],
                name=f"continuity_vehicle_{vehicle}_arc_{currentArc}"
            )


def addObjectiveFunction(inputData, model) -> None:
    print("Writing the objective function:", end=" ")
    model.addConstr(model._totalDelay ==
                    grb.quicksum(
                        model._delay[vehicle][arc] for vehicle in model._delay for arc in
                        model._delay[vehicle]),
                    name="total_delay_constraint")
    model.setObjective(model._totalDelay)
    print("minimization of total delay")
    model.ModelSense = grb.GRB.MINIMIZE
