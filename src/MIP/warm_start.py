from __future__ import annotations
import itertools
import gurobipy as grb
from utils.classes import CompleteSolution, HeuristicSolution
from MIP import StaggeredRoutingModel


def _set_binary_variables_warm_start(model: StaggeredRoutingModel,
                                     warm_start: CompleteSolution | HeuristicSolution) -> None:
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


def _set_continuous_variables_warm_start(model: StaggeredRoutingModel, warm_start: CompleteSolution) -> None:
    """Set initial values for continuous variables in the warm start model."""
    for vehicle in model._departure:
        for position, arc in enumerate(model._departure[vehicle]):
            schedule_value = warm_start.congested_schedule[vehicle][position]
            delay_value = warm_start.delays_on_arcs[vehicle][position]

            # Set start value for departure variable
            model._departure[vehicle][arc].Start = schedule_value
            assert model._departure[vehicle][arc]._lb - 1e-6 <= schedule_value <= model._departure[vehicle][
                arc]._ub + 1e-6, \
                f"Departure bounds violated: {model._departure[vehicle][arc]._lb} <= {schedule_value} <= {model._departure[vehicle][arc]._ub}"

            # Set start value for delay variable if it exists
            if isinstance(model._delay[vehicle][arc], grb.Var):
                model._delay[vehicle][arc].Start = delay_value
                assert model._delay[vehicle][arc]._lb - 1e-6 <= delay_value <= model._delay[vehicle][arc]._ub + 1e-6, \
                    f"Delay bounds violated: {model._delay[vehicle][arc]._lb} <= {delay_value} <= {model._delay[vehicle][arc]._ub}"


def set_warm_start_model(model: StaggeredRoutingModel, warm_start: CompleteSolution | HeuristicSolution) -> None:
    """Apply warm start settings to the model."""
    _set_binary_variables_warm_start(model, warm_start)
    _set_continuous_variables_warm_start(model, warm_start)
