from MIP import StaggeredRoutingModel
from instance_module.instance import Instance
from collections import namedtuple
from input_data import TOLERANCE

# TODO: remove named tuple
BinariesBounds = namedtuple("BinariesBounds", ["lb_alpha", "ub_alpha", "lb_beta", "ub_beta", "lb_gamma", "ub_gamma"])


def _get_bounds_for_binaries(
        first_vehicle: int, second_vehicle: int, arc: int, instance: Instance
) -> BinariesBounds:
    """Calculate bounds for binary variables (alpha, beta, gamma) between two vehicles on a specific arc."""
    lb_alpha = lb_beta = lb_gamma = 0
    ub_alpha = ub_beta = ub_gamma = 1

    # Get positions and timing bounds for the vehicles on the arc
    pos_1 = instance.trip_routes[first_vehicle].index(arc)
    pos_2 = instance.trip_routes[second_vehicle].index(arc)

    e_e_1, e_l_1 = (
        instance.earliest_departure_times[first_vehicle][pos_1],
        instance.latest_departure_times[first_vehicle][pos_1],
    )
    e_e_2, e_l_2 = (
        instance.earliest_departure_times[second_vehicle][pos_2],
        instance.latest_departure_times[second_vehicle][pos_2],
    )
    l_e_2, l_l_2 = (
        instance.earliest_departure_times[second_vehicle][pos_2 + 1],
        instance.latest_departure_times[second_vehicle][pos_2 + 1],
    )

    # Use tolerances in comparisons
    alpha_must_be_one = e_l_2 < e_e_1 - TOLERANCE
    beta_must_be_one = e_l_1 < l_e_2 - TOLERANCE
    gamma_must_be_one = alpha_must_be_one and beta_must_be_one

    alpha_must_be_zero = e_l_1 < e_e_2 - TOLERANCE
    beta_must_be_zero = l_l_2 < e_e_1 - TOLERANCE

    # Adjust bounds based on conditions
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


def _add_conflict_variables_between_two_vehicles(model: StaggeredRoutingModel, arc: int, first_vehicle: int,
                                                 second_vehicle: int,
                                                 instance: Instance) -> None:
    """Add binary variables (alpha, beta, gamma) for a vehicle pair on a specific arc."""
    bounds = _get_bounds_for_binaries(first_vehicle, second_vehicle, arc, instance)

    # Alpha variable
    alpha_name = f"alpha_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model.add_conflict_pair_var(arc, first_vehicle, second_vehicle, alpha_name, bounds.lb_alpha, bounds.ub_alpha,
                                "alpha")

    # Beta variable
    beta_name = f"beta_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model.add_conflict_pair_var(arc, first_vehicle, second_vehicle, beta_name, bounds.lb_beta, bounds.ub_beta, "beta")

    # Gamma variable
    gamma_name = f"gamma_arc_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
    model.add_conflict_pair_var(arc, first_vehicle, second_vehicle, gamma_name, bounds.lb_gamma, bounds.ub_gamma,
                                "gamma")


def _add_conflict_variables_among_vehicles_in_conflicting_set(
        model: StaggeredRoutingModel, arc: int, conflicting_set: list[int], instance: Instance
) -> None:
    """Add conflict variables for all pairs of vehicles in a conflicting set."""
    model.add_arc_conflict_vars(arc)

    for first_trip in conflicting_set:
        # Initialize dictionaries for the first vehicle if not already present
        if not model.has_trip_conflict_vars_on_arc(arc, first_trip):
            model.add_trip_to_arc_conflict_vars(arc, first_trip)

        for second_trip in conflicting_set:
            if first_trip == second_trip:
                continue

            # Initialize dictionaries for the second vehicle if not already present
            if not model.has_trip_conflict_vars_on_arc(arc, second_trip):
                model.add_trip_to_arc_conflict_vars(arc, second_trip)

            # Add conflict variables between the two vehicles
            if first_trip < second_trip:
                _add_conflict_variables_between_two_vehicles(model, arc, first_trip, second_trip, instance)
                _add_conflict_variables_between_two_vehicles(model, arc, second_trip, first_trip, instance)


def add_conflict_variables(model: StaggeredRoutingModel, instance: Instance) -> None:
    """Add all conflict variables for each arc and its conflicting set."""
    print("Creating conflict variables ...", end=" ")

    for arc, conflicting_set in enumerate(instance.conflicting_sets):
        if conflicting_set:
            _add_conflict_variables_among_vehicles_in_conflicting_set(model, arc, conflicting_set, instance)

    print("done!")
