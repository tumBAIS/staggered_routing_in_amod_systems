from gurobipy import Model
from instance_module.instance import Instance
import gurobipy as grb
from collections import namedtuple

BinariesBounds = namedtuple("BinariesBounds", ["lbAlpha", "ubAlpha", "lbBeta", "ubBeta", "lbGamma", "ubGamma"])


def _get_bounds_for_binaries(firstVehicle: int, secondVehicle: int, arc: int, instance: Instance) -> BinariesBounds:
    lbAlpha = 0
    lbBeta = 0
    lbGamma = 0
    ubAlpha = 1
    ubBeta = 1
    ubGamma = 1

    position_1 = instance.trip_routes[firstVehicle].index(arc)
    position_2 = instance.trip_routes[secondVehicle].index(arc)
    e_e_1 = instance.earliest_departure_times[firstVehicle][position_1]
    e_l_1 = instance.latest_departure_times[firstVehicle][position_1]
    e_e_2 = instance.earliest_departure_times[secondVehicle][position_2]
    e_l_2 = instance.latest_departure_times[secondVehicle][position_2]
    l_e_2 = instance.earliest_departure_times[secondVehicle][position_2 + 1]
    l_l_2 = instance.latest_departure_times[secondVehicle][position_2 + 1]

    alpha_must_be_one = e_l_2 < e_e_1
    beta_must_be_one = e_l_1 < l_e_2
    gamma_must_be_one = alpha_must_be_one and beta_must_be_one

    alpha_must_be_zero = e_l_1 < e_e_2
    beta_must_be_zero = l_l_2 < e_e_1

    if alpha_must_be_one:
        assert alpha_must_be_zero is False
        lbAlpha = ubAlpha = 1
    if beta_must_be_one:
        assert beta_must_be_zero is False
        lbBeta = ubBeta = 1
    if gamma_must_be_one:
        lbGamma = ubGamma = 1

    if alpha_must_be_zero or beta_must_be_zero:
        lbAlpha = ubAlpha = 0
        lbBeta = ubBeta = 0
        lbGamma = ubGamma = 0

    return BinariesBounds(lbAlpha=lbAlpha, ubAlpha=ubAlpha, lbBeta=lbBeta, ubBeta=ubBeta, lbGamma=lbGamma,
                          ubGamma=ubGamma)


def _store_bounds_in_variables(model: Model, arc: int, firstVehicle: int, secondVehicle: int,
                               binariesBounds: BinariesBounds) -> None:
    if isinstance(model._alpha[arc][firstVehicle][secondVehicle], grb.Var):
        model._alpha[arc][firstVehicle][secondVehicle]._lb = binariesBounds.lbAlpha
        model._alpha[arc][firstVehicle][secondVehicle]._ub = binariesBounds.ubAlpha
    if isinstance(model._beta[arc][firstVehicle][secondVehicle], grb.Var):
        model._beta[arc][firstVehicle][secondVehicle]._lb = binariesBounds.lbBeta
        model._beta[arc][firstVehicle][secondVehicle]._ub = binariesBounds.ubBeta

    if isinstance(model._gamma[arc][firstVehicle][secondVehicle], grb.Var):
        model._gamma[arc][firstVehicle][secondVehicle]._lb = binariesBounds.lbGamma
        model._gamma[arc][firstVehicle][secondVehicle]._ub = binariesBounds.ubGamma


def _add_conflict_variables_between_two_vehicles(model: Model, arc: int, firstVehicle: int, secondVehicle: int,
                                                 instance: Instance):
    binariesBounds = _get_bounds_for_binaries(firstVehicle, secondVehicle, arc, instance)

    alphaName = f"alpha_arc_{str(arc)}_vehicles_{str(firstVehicle)}_{str(secondVehicle)}"
    if binariesBounds.lbAlpha != binariesBounds.ubAlpha:
        model._alpha[arc][firstVehicle][secondVehicle] = model.addVar(vtype=grb.GRB.BINARY,
                                                                      name=alphaName,
                                                                      lb=binariesBounds.lbAlpha,
                                                                      ub=binariesBounds.ubAlpha)
    else:
        model._alpha[arc][firstVehicle][secondVehicle] = binariesBounds.lbAlpha
    betaName = f"beta_arc_{str(arc)}_vehicles_{str(firstVehicle)}_{str(secondVehicle)}"
    if binariesBounds.lbBeta != binariesBounds.ubBeta:
        model._beta[arc][firstVehicle][secondVehicle] = model.addVar(vtype=grb.GRB.BINARY,
                                                                     name=betaName,
                                                                     lb=binariesBounds.lbBeta,
                                                                     ub=binariesBounds.ubBeta)
    else:
        model._beta[arc][firstVehicle][secondVehicle] = binariesBounds.lbBeta

    gammaName = f"gamma_arc_{str(arc)}_vehicles_{str(firstVehicle)}_{str(secondVehicle)}"

    if binariesBounds.lbGamma != binariesBounds.ubGamma:

        model._gamma[arc][firstVehicle][secondVehicle] = model.addVar(vtype=grb.GRB.BINARY,
                                                                      name=gammaName,
                                                                      lb=binariesBounds.lbGamma,
                                                                      ub=binariesBounds.ubGamma)
    else:
        model._gamma[arc][firstVehicle][secondVehicle] = binariesBounds.lbGamma

    _store_bounds_in_variables(model, arc, firstVehicle, secondVehicle, binariesBounds)
    return


def _add_conflict_variables_among_vehicles_in_conflicting_set(model: Model, arc: int,
                                                              conflictingSet: list[int], instance: Instance) -> None:
    model._alpha[arc] = {}
    model._beta[arc] = {}
    model._gamma[arc] = {}

    for firstVehicle in conflictingSet:
        if firstVehicle not in model._alpha[arc]:
            model._alpha[arc][firstVehicle] = {}
            model._beta[arc][firstVehicle] = {}
            model._gamma[arc][firstVehicle] = {}

        for secondVehicle in conflictingSet:
            if secondVehicle == firstVehicle:
                continue
            if secondVehicle not in model._alpha[arc]:
                model._alpha[arc][secondVehicle] = {}
                model._beta[arc][secondVehicle] = {}
                model._gamma[arc][secondVehicle] = {}

            if firstVehicle < secondVehicle:
                _add_conflict_variables_between_two_vehicles(model, arc, firstVehicle, secondVehicle, instance)
                _add_conflict_variables_between_two_vehicles(model, arc, secondVehicle, firstVehicle, instance)


def add_conflict_variables(model: Model, instance: Instance) -> None:
    print("Creating conflict variables ...", end=" ")
    model._alpha = {}
    model._beta = {}
    model._gamma = {}
    for arc, conflictingSet in enumerate(instance.conflicting_sets):
        if conflictingSet:
            _add_conflict_variables_among_vehicles_in_conflicting_set(model, arc, conflictingSet, instance)
    print("done!")
