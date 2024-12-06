from __future__ import annotations

import itertools
import gurobipy as grb
from gurobipy import Model

from utils.classes import CompleteSolution, HeuristicSolution


def _set_binaries_warm_start_model(model: Model, warmStart: CompleteSolution | HeuristicSolution) -> None:
    for arc in model._gamma:
        for firstVehicle, secondVehicle in itertools.combinations(model._gamma[arc], 2):
            if warmStart.binaries.gamma[arc][firstVehicle][secondVehicle] != -1:
                if isinstance(model._alpha[arc][firstVehicle][secondVehicle], grb.Var):
                    model._alpha[arc][firstVehicle][secondVehicle].Start = \
                        warmStart.binaries.alpha[arc][firstVehicle][secondVehicle]
                if isinstance(model._beta[arc][firstVehicle][secondVehicle], grb.Var):
                    model._beta[arc][firstVehicle][secondVehicle].Start = \
                        warmStart.binaries.beta[arc][firstVehicle][secondVehicle]
                if isinstance(model._gamma[arc][firstVehicle][secondVehicle], grb.Var):
                    model._gamma[arc][firstVehicle][secondVehicle].Start = \
                        warmStart.binaries.gamma[arc][firstVehicle][secondVehicle]

            if warmStart.binaries.gamma[arc][secondVehicle][firstVehicle] != -1:
                if isinstance(model._alpha[arc][secondVehicle][firstVehicle], grb.Var):
                    model._alpha[arc][secondVehicle][firstVehicle].Start = \
                        warmStart.binaries.alpha[arc][secondVehicle][firstVehicle]
                if isinstance(model._beta[arc][secondVehicle][firstVehicle], grb.Var):
                    model._beta[arc][secondVehicle][firstVehicle].Start = \
                        warmStart.binaries.beta[arc][secondVehicle][firstVehicle]
                if isinstance(model._gamma[arc][secondVehicle][firstVehicle], grb.Var):
                    model._gamma[arc][secondVehicle][firstVehicle].Start = \
                        warmStart.binaries.gamma[arc][secondVehicle][firstVehicle]
    return


def _set_continuous_variables_warm_start_model(model: Model, warmStart: CompleteSolution):
    for vehicle in model._departure:
        for position, arc in enumerate(model._departure[vehicle]):
            model._departure[vehicle][arc].Start = warmStart.congested_schedule[vehicle][position]
            assert model._departure[vehicle][arc]._lb - 1e-6 <= warmStart.congested_schedule[vehicle][position] <= \
                   model._departure[vehicle][arc]._ub + 1e-6, \
                f"{model._departure[vehicle][arc]._lb} <\= {warmStart.congested_schedule[vehicle][position]} <\= \
                   {model._departure[vehicle][arc]._ub}"
            if isinstance(model._delay[vehicle][arc], grb.Var):
                model._delay[vehicle][arc].Start = warmStart.delays_on_arcs[vehicle][position]
                assert model._delay[vehicle][arc]._lb - 1e-6 <= warmStart.delays_on_arcs[vehicle][position] <= \
                       model._delay[vehicle][arc]._ub + 1e-6, \
                    rf"{model._delay[vehicle][arc]._lb} <\= {warmStart.delays_on_arcs[vehicle][position]} <\= \
                   {model._delay[vehicle][arc]._ub}, vehicle: {vehicle}, arc: {arc}, " \
                    f"vehicle schedule: {warmStart.congested_schedule[vehicle]}, vehicle delays: {warmStart.delays_on_arcs[vehicle]}"


def set_warm_start_model(model: Model, warmStart: CompleteSolution | HeuristicSolution) -> None:
    _set_binaries_warm_start_model(model, warmStart)
    _set_continuous_variables_warm_start_model(model, warmStart)
    return
