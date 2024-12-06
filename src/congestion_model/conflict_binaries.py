import itertools
from dataclasses import dataclass

from utils.classes import Binaries
from utils.aliases import VehicleSchedules
from input_data import CONSTR_TOLERANCE, TOLERANCE


@dataclass
class VehiclePair:
    arc: int
    vehicleOne: int
    departureOne: float
    arrivalOne: float
    vehicleTwo: int
    departureTwo: float
    arrivalTwo: float


def _set_alpha_pair(binaries: Binaries, vehiclePair: VehiclePair) -> None:
    alphaTie = abs(vehiclePair.departureOne - vehiclePair.departureTwo) < CONSTR_TOLERANCE - TOLERANCE
    departureOneAfterTwo = vehiclePair.departureOne >= vehiclePair.departureTwo + (CONSTR_TOLERANCE - TOLERANCE)

    if alphaTie:
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = -1
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = -1
    elif departureOneAfterTwo:
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = 1
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = 0
    else:
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = 0
        binaries.alpha[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = 1


def _set_beta_vehicle_one(binaries: Binaries, vehiclePair: VehiclePair) -> None:
    betaTieOne = abs(vehiclePair.departureOne - vehiclePair.arrivalTwo) < CONSTR_TOLERANCE - TOLERANCE
    departureOneAfterArrivalTwo = vehiclePair.departureOne >= vehiclePair.arrivalTwo + (CONSTR_TOLERANCE - TOLERANCE)

    if betaTieOne:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = -1
    elif departureOneAfterArrivalTwo:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = 0
    else:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = 1


def _set_beta_vehicle_two(binaries: Binaries, vehiclePair: VehiclePair) -> None:
    betaTieTwo: bool = abs(vehiclePair.departureTwo - vehiclePair.arrivalOne) < CONSTR_TOLERANCE - TOLERANCE
    departureTwoAfterArrivalOne: bool = vehiclePair.departureTwo >= vehiclePair.arrivalOne + (
            CONSTR_TOLERANCE - TOLERANCE)
    if betaTieTwo:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = -1
    elif departureTwoAfterArrivalOne:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = 0
    else:
        binaries.beta[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = 1


def _set_gamma_vehicle_one(binaries: Binaries, vehiclePair: VehiclePair) -> None:
    binariesOneAreUndefined = (
            binaries.alpha[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] == -1
            or binaries.beta[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] == -1
    )

    if binariesOneAreUndefined:
        binaries.gamma[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = -1
    else:
        oneOverlapsWithTwo = (
                binaries.alpha[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] == 1
                and binaries.beta[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] == 1
        )

        binaries.gamma[vehiclePair.arc][vehiclePair.vehicleOne][vehiclePair.vehicleTwo] = (
            1 if oneOverlapsWithTwo else 0
        )


def _set_gamma_vehicle_two(binaries, vehiclePair: VehiclePair):
    binariesTwoAreUndefined = (
            binaries.alpha[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] == -1
            or binaries.beta[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] == -1
    )

    if binariesTwoAreUndefined:
        binaries.gamma[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = -1
    else:
        twoOverlapsWithOne = (
                binaries.alpha[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] == 1
                and binaries.beta[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] == 1
        )

        binaries.gamma[vehiclePair.arc][vehiclePair.vehicleTwo][vehiclePair.vehicleOne] = (
            1 if twoOverlapsWithOne else 0
        )


def _create_binaries_vehicle_entry(binaries: Binaries, arc: int, vehiclePair: VehiclePair) -> None:
    if vehiclePair.vehicleOne not in binaries.alpha[arc]:
        binaries.alpha[arc][vehiclePair.vehicleOne] = {}
        binaries.beta[arc][vehiclePair.vehicleOne] = {}
        binaries.gamma[arc][vehiclePair.vehicleOne] = {}

    if vehiclePair.vehicleTwo not in binaries.alpha[arc]:
        binaries.alpha[arc][vehiclePair.vehicleTwo] = {}
        binaries.beta[arc][vehiclePair.vehicleTwo] = {}
        binaries.gamma[arc][vehiclePair.vehicleTwo] = {}


def _create_binaries_arc_entry(binaries: Binaries, arc: int) -> None:
    binaries.alpha[arc] = {}
    binaries.beta[arc] = {}
    binaries.gamma[arc] = {}


def _set_binaries_between_pair(binaries: Binaries, vehiclePair: VehiclePair):
    _set_alpha_pair(binaries, vehiclePair)
    _set_beta_vehicle_one(binaries, vehiclePair)
    _set_beta_vehicle_two(binaries, vehiclePair)
    _set_gamma_vehicle_one(binaries, vehiclePair)
    _set_gamma_vehicle_two(binaries, vehiclePair)


def get_conflict_binaries(conflictingSets: list[list[int]], shortestPaths: list[list[int]],
                          congestedSchedule: VehicleSchedules, printVariables=False) -> Binaries:
    if printVariables:
        print("Computing conflicting binaries ... ", end="")
    binaries = Binaries({}, {}, {})
    for arc, conflictingSet in enumerate(conflictingSets):
        if arc == 0 or not conflictingSet:
            continue
        _create_binaries_arc_entry(binaries, arc)
        for vehicleOne, vehicleTwo in itertools.combinations(conflictingSet, 2):
            positionOne = shortestPaths[vehicleOne].index(arc)
            positionTwo = shortestPaths[vehicleTwo].index(arc)
            vehiclePair = VehiclePair(arc=arc,
                                      vehicleOne=vehicleOne,
                                      vehicleTwo=vehicleTwo,
                                      departureOne=congestedSchedule[vehicleOne][positionOne],
                                      arrivalOne=congestedSchedule[vehicleOne][positionOne + 1],
                                      departureTwo=congestedSchedule[vehicleTwo][positionTwo],
                                      arrivalTwo=congestedSchedule[vehicleTwo][positionTwo + 1])
            _create_binaries_vehicle_entry(binaries, arc, vehiclePair)
            _set_binaries_between_pair(binaries, vehiclePair)
    numberOfBinaries = 3 * sum(
        1 for arc in binaries.alpha for firstVehicle in binaries.alpha[arc] for _ in binaries.alpha[arc][firstVehicle])
    if printVariables:
        print(f"done! The number of binary variables is {numberOfBinaries}")
    return binaries


def get_flow_from_binaries(instance, gammas) -> list[list[int]]:
    flows = []
    for vehicle, path in enumerate(instance.trip_routes):
        vehicle_flows = []
        for pos, arc in enumerate(path):
            if arc in gammas and vehicle in gammas[arc]:
                flow = sum(gammas[arc][vehicle][x] for x in gammas[arc][vehicle])
            else:
                flow = 0
            vehicle_flows.append(flow)
        flows.append(vehicle_flows)
    return flows
