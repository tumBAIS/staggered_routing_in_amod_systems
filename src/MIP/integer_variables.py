from gurobipy import Model
from instance_module.instance import Instance
import gurobipy as grb
from collections import namedtuple

BinariesBounds = namedtuple("BinariesBounds", ["lb_alpha", "ub_alpha", "lb_beta", "ub_beta", "lb_gamma", "ub_gamma"])


def _get_bounds_for_binaries(first_vehicle: int, second_vehicle: int, arc: int, instance: Instance) -> BinariesBounds:
    """Calculate bounds for binary variables (alpha, beta, gamma) between two vehicles on a specific arc."""
    lb_alpha = lb_beta = lb_gamma = 0
    ub_alpha = ub_beta = ub_gamma = 1

    pos_1 = instance.trip_routes[first_vehicle].index(arc)
    pos_2 = instance.trip_routes[second_vehicle].index(arc)
    e_e_1, e_l_1 = instance.earliest_departure_times[first_vehicle][pos_1], \
        instance.latest_departure_times[first_vehicle][pos_1]
    e_e_2, e_l_2 = instance.earliest_departure_times[second_vehicle][pos_2], \
        instance.latest_departure_times[second_vehicle][pos_2]
    l_e_2, l_l_2 = instance.earliest_departure_times[second_vehicle][pos_2 + 1], \
        instance.latest_departure_times[second_vehicle][pos_2 + 1]

    alpha_must_be_one = e_l_2 < e_e_1
    beta_must_be_one = e_l_1 < l_e_2
    gamma_must_be_one = alpha_must_be_one and beta_must_be_one

    alpha_must_be_zero = e_l_1 < e_e_2
    beta_must_be_zero = l_l_2 < e_e_1

    if alpha_must_be_one:
        assert not alpha_must_be_zero, "Conflicting bounds for alpha."
        lb_alpha = ub_alpha = 1
    if beta_must_be_one:
        assert not beta_must_be_zero, "Conflicting bounds for beta."
        lb_beta = ub_beta = 1
    if gamma_must_be_one:
        lb_gamma = ub_gamma = 1

    if alpha_must_be_zero or beta_must_be_zero:
        lb_alpha = ub_alpha = lb_beta = ub_beta = lb_gamma = ub_gamma = 0

    return BinariesBounds(lb_alpha, ub_alpha, lb_beta, ub_beta, lb_gamma, ub_gamma)


def _store_bounds_in_variables(model: Model, arc: int, first_vehicle: int, second_vehicle: int,
                               bounds: BinariesBounds) -> None:
    """Store calculated bounds into binary variables."""
    if isinstance(model._alpha[arc][first_vehicle][second_vehicle], grb.Var):
        model._alpha[arc][first_vehicle][second_vehicle]._lb = bounds.lb_alpha
        model._alpha[arc][first_vehicle][second_vehicle]._ub = bounds.ub_alpha
    if isinstance(model._beta[arc][first_vehicle][second_vehicle], grb.Var):
        model._beta[arc][first_vehicle][second_vehicle]._lb = bounds.lb_beta
        model._beta[arc][first_vehicle][second_vehicle]._ub = bounds.ub_beta
    if isinstance(model._gamma[arc][first_vehicle][second_vehicle], grb.Var):
        model._gamma[arc][first_vehicle][second_vehicle]._lb = bounds.lb_gamma
        model._gamma[arc][first_vehicle][second_vehicle]._ub = bounds.ub_gamma


def _add_conflict_variables_between_two_vehicles(model: Model, arc: int, first_vehicle: int, second_vehicle: int,
                                                 instance: Instance) -> None:
    """Add binary variables (alpha, beta, gamma) for a vehicle pair on a specific arc."""
    bounds = _get_bounds_for_binaries(first_vehicle, second_vehicle, arc, instance)

    # Alpha variable
    alpha_name = f"alpha_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model._alpha[arc][first_vehicle][second_vehicle] = (
        model.addVar(vtype=grb.GRB.BINARY, name=alpha_name, lb=bounds.lb_alpha, ub=bounds.ub_alpha)
        if bounds.lb_alpha != bounds.ub_alpha else bounds.lb_alpha
    )

    # Beta variable
    beta_name = f"beta_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model._beta[arc][first_vehicle][second_vehicle] = (
        model.addVar(vtype=grb.GRB.BINARY, name=beta_name, lb=bounds.lb_beta, ub=bounds.ub_beta)
        if bounds.lb_beta != bounds.ub_beta else bounds.lb_beta
    )

    # Gamma variable
    gamma_name = f"gamma_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model._gamma[arc][first_vehicle][second_vehicle] = (
        model.addVar(vtype=grb.GRB.BINARY, name=gamma_name, lb=bounds.lb_gamma, ub=bounds.ub_gamma)
        if bounds.lb_gamma != bounds.ub_gamma else bounds.lb_gamma
    )

    _store_bounds_in_variables(model, arc, first_vehicle, second_vehicle, bounds)


def _add_conflict_variables_among_vehicles_in_conflicting_set(
        model: Model, arc: int, conflicting_set: list[int], instance: Instance
) -> None:
    """Add conflict variables for all pairs of vehicles in a conflicting set."""
    model._alpha[arc] = {}
    model._beta[arc] = {}
    model._gamma[arc] = {}

    for first_vehicle in conflicting_set:
        # Initialize dictionaries for the first vehicle if not already present
        if first_vehicle not in model._alpha[arc]:
            model._alpha[arc][first_vehicle] = {}
            model._beta[arc][first_vehicle] = {}
            model._gamma[arc][first_vehicle] = {}

        for second_vehicle in conflicting_set:
            if first_vehicle == second_vehicle:
                continue

            # Initialize dictionaries for the second vehicle if not already present
            if second_vehicle not in model._alpha[arc]:
                model._alpha[arc][second_vehicle] = {}
                model._beta[arc][second_vehicle] = {}
                model._gamma[arc][second_vehicle] = {}

            # Add conflict variables between the two vehicles
            if first_vehicle < second_vehicle:
                _add_conflict_variables_between_two_vehicles(model, arc, first_vehicle, second_vehicle, instance)
                _add_conflict_variables_between_two_vehicles(model, arc, second_vehicle, first_vehicle, instance)


def add_conflict_variables(model: Model, instance: Instance) -> None:
    """Add all conflict variables for each arc and its conflicting set."""
    print("Creating conflict variables ...", end=" ")
    model._alpha, model._beta, model._gamma = {}, {}, {}

    for arc, conflicting_set in enumerate(instance.conflicting_sets):
        if conflicting_set:
            _add_conflict_variables_among_vehicles_in_conflicting_set(model, arc, conflicting_set, instance)

    print("done!")
