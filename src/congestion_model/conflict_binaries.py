import itertools
from dataclasses import dataclass

from utils.classes import Binaries
from utils.aliases import VehicleSchedules
from input_data import CONSTR_TOLERANCE, TOLERANCE


@dataclass
class VehiclePair:
    arc: int
    vehicle_one: int
    departure_one: float
    arrival_one: float
    vehicle_two: int
    departure_two: float
    arrival_two: float


def set_alpha_pair(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    alpha_tie = abs(vehicle_pair.departure_one - vehicle_pair.departure_two) < CONSTR_TOLERANCE - TOLERANCE
    departure_one_after_two = vehicle_pair.departure_one >= vehicle_pair.departure_two + (CONSTR_TOLERANCE - TOLERANCE)

    if alpha_tie:
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = -1
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = -1
    elif departure_one_after_two:
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 1
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 0
    else:
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 0
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 1


def set_beta_vehicle_one(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    beta_tie_one = abs(vehicle_pair.departure_one - vehicle_pair.arrival_two) < CONSTR_TOLERANCE - TOLERANCE
    departure_one_after_arrival_two = vehicle_pair.departure_one >= vehicle_pair.arrival_two + (
                CONSTR_TOLERANCE - TOLERANCE)

    if beta_tie_one:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = -1
    elif departure_one_after_arrival_two:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 0
    else:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 1


def set_beta_vehicle_two(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    beta_tie_two = abs(vehicle_pair.departure_two - vehicle_pair.arrival_one) < CONSTR_TOLERANCE - TOLERANCE
    departure_two_after_arrival_one = vehicle_pair.departure_two >= vehicle_pair.arrival_one + (
                CONSTR_TOLERANCE - TOLERANCE)

    if beta_tie_two:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = -1
    elif departure_two_after_arrival_one:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 0
    else:
        binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 1


def set_gamma_vehicle_one(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    binaries_one_are_undefined = (
            binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] == -1
            or binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] == -1
    )

    if binaries_one_are_undefined:
        binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = -1
    else:
        one_overlaps_with_two = (
                binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] == 1
                and binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] == 1
        )

        binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = (
            1 if one_overlaps_with_two else 0
        )


def set_gamma_vehicle_two(binaries, vehicle_pair: VehiclePair):
    binaries_two_are_undefined = (
            binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] == -1
            or binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] == -1
    )

    if binaries_two_are_undefined:
        binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = -1
    else:
        two_overlaps_with_one = (
                binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] == 1
                and binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] == 1
        )

        binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = (
            1 if two_overlaps_with_one else 0
        )


def create_binaries_vehicle_entry(binaries: Binaries, arc: int, vehicle_pair: VehiclePair) -> None:
    if vehicle_pair.vehicle_one not in binaries.alpha[arc]:
        binaries.alpha[arc][vehicle_pair.vehicle_one] = {}
        binaries.beta[arc][vehicle_pair.vehicle_one] = {}
        binaries.gamma[arc][vehicle_pair.vehicle_one] = {}

    if vehicle_pair.vehicle_two not in binaries.alpha[arc]:
        binaries.alpha[arc][vehicle_pair.vehicle_two] = {}
        binaries.beta[arc][vehicle_pair.vehicle_two] = {}
        binaries.gamma[arc][vehicle_pair.vehicle_two] = {}


def create_binaries_arc_entry(binaries: Binaries, arc: int) -> None:
    binaries.alpha[arc] = {}
    binaries.beta[arc] = {}
    binaries.gamma[arc] = {}


def set_binaries_between_pair(binaries: Binaries, vehicle_pair: VehiclePair):
    set_alpha_pair(binaries, vehicle_pair)
    set_beta_vehicle_one(binaries, vehicle_pair)
    set_beta_vehicle_two(binaries, vehicle_pair)
    set_gamma_vehicle_one(binaries, vehicle_pair)
    set_gamma_vehicle_two(binaries, vehicle_pair)


def get_conflict_binaries(conflicting_sets: list[list[int]], shortest_paths: list[list[int]],
                          congested_schedule: VehicleSchedules, print_variables=False) -> Binaries:
    if print_variables:
        print("Computing conflicting binaries ... ", end="")
    binaries = Binaries({}, {}, {})
    for arc, conflicting_set in enumerate(conflicting_sets):
        if arc == 0 or not conflicting_set:
            continue
        create_binaries_arc_entry(binaries, arc)
        for vehicle_one, vehicle_two in itertools.combinations(conflicting_set, 2):
            position_one = shortest_paths[vehicle_one].index(arc)
            position_two = shortest_paths[vehicle_two].index(arc)
            vehicle_pair = VehiclePair(arc=arc,
                                       vehicle_one=vehicle_one,
                                       vehicle_two=vehicle_two,
                                       departure_one=congested_schedule[vehicle_one][position_one],
                                       arrival_one=congested_schedule[vehicle_one][position_one + 1],
                                       departure_two=congested_schedule[vehicle_two][position_two],
                                       arrival_two=congested_schedule[vehicle_two][position_two + 1])
            create_binaries_vehicle_entry(binaries, arc, vehicle_pair)
            set_binaries_between_pair(binaries, vehicle_pair)
    number_of_binaries = 3 * sum(
        1 for arc in binaries.alpha for first_vehicle in binaries.alpha[arc] for _ in
        binaries.alpha[arc][first_vehicle])
    if print_variables:
        print(f"done! The number of binary variables is {number_of_binaries}")
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
