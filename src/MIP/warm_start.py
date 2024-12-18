from __future__ import annotations
from problem.solution import Solution, HeuristicSolution
from MIP import StaggeredRoutingModel
from problem.instance import Instance


def set_warm_start_model(model: StaggeredRoutingModel,
                         warm_start: Solution | HeuristicSolution,
                         instance: Instance) -> None:
    """Set initial values for binary variables in the warm start model."""
    for arc in model.get_list_conflicting_arcs():
        for first_vehicle, second_vehicle in model.get_arc_conflicting_pairs(arc):
            if warm_start.binaries.gamma[arc][first_vehicle][second_vehicle] != -1:
                # First trip binaries
                first_alpha_to_set = warm_start.binaries.alpha[arc][first_vehicle][second_vehicle]
                first_beta_to_set = warm_start.binaries.beta[arc][first_vehicle][second_vehicle]
                first_gamma_to_set = warm_start.binaries.gamma[arc][first_vehicle][second_vehicle]
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "alpha", first_alpha_to_set, "start")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "beta", first_beta_to_set, "start")
                model.set_conflicting_var(first_vehicle, second_vehicle, arc, "gamma", first_gamma_to_set, "start")

                # Second trip binaries (roles inverted)
                second_alpha_to_set = warm_start.binaries.alpha[arc][second_vehicle][first_vehicle]
                second_beta_to_set = warm_start.binaries.beta[arc][second_vehicle][first_vehicle]
                second_gamma_to_set = warm_start.binaries.gamma[arc][second_vehicle][first_vehicle]
                model.set_conflicting_var(second_vehicle, first_vehicle, arc, "alpha", second_alpha_to_set, "start")
                model.set_conflicting_var(second_vehicle, first_vehicle, arc, "beta", second_beta_to_set, "start")
                model.set_conflicting_var(second_vehicle, first_vehicle, arc, "gamma", second_gamma_to_set, "start")

    for trip, route in enumerate(instance.trip_routes):
        for position, arc in enumerate(route):
            schedule_value = warm_start.congested_schedule[trip][position]
            delay_value = warm_start.delays_on_arcs[trip][position]

            model.set_continuous_var(trip, arc, "departure", schedule_value, "start")
            model.set_continuous_var(trip, arc, "delay", delay_value, "start")
