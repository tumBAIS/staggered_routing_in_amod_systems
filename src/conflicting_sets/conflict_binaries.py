import itertools
from dataclasses import dataclass
from problem.solution import Binaries
from utils.aliases import *
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


def update_alpha(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    alpha_tie = abs(vehicle_pair.departure_one - vehicle_pair.departure_two) < CONSTR_TOLERANCE - TOLERANCE
    departure_one_after_two = vehicle_pair.departure_one >= vehicle_pair.departure_two + (CONSTR_TOLERANCE - TOLERANCE)

    if alpha_tie:
        value = -1
    elif departure_one_after_two:
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 1
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 0
        return
    else:
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = 0
        binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = 1
        return

    binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = value
    binaries.alpha[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = value


def update_beta(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    def set_beta(vehicle, departure, arrival):
        beta_tie = abs(departure - arrival) < CONSTR_TOLERANCE - TOLERANCE
        departure_after_arrival = departure >= arrival + (CONSTR_TOLERANCE - TOLERANCE)

        if beta_tie:
            return -1
        return 0 if departure_after_arrival else 1

    binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = set_beta(
        vehicle_pair.vehicle_one, vehicle_pair.departure_one, vehicle_pair.arrival_two
    )
    binaries.beta[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = set_beta(
        vehicle_pair.vehicle_two, vehicle_pair.departure_two, vehicle_pair.arrival_one
    )


def update_gamma(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    def set_gamma(vehicle_one, vehicle_two):
        alpha = binaries.alpha[vehicle_pair.arc][vehicle_one][vehicle_two]
        beta = binaries.beta[vehicle_pair.arc][vehicle_one][vehicle_two]

        if alpha == -1 or beta == -1:
            return -1
        return 1 if alpha == 1 and beta == 1 else 0

    binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_one][vehicle_pair.vehicle_two] = set_gamma(
        vehicle_pair.vehicle_one, vehicle_pair.vehicle_two
    )
    binaries.gamma[vehicle_pair.arc][vehicle_pair.vehicle_two][vehicle_pair.vehicle_one] = set_gamma(
        vehicle_pair.vehicle_two, vehicle_pair.vehicle_one
    )


def initialize_binaries(binaries: Binaries, arc: int, vehicle_pair: VehiclePair) -> None:
    def ensure_vehicle_entry(vehicle):
        if vehicle not in binaries.alpha[arc]:
            binaries.alpha[arc][vehicle] = {}
            binaries.beta[arc][vehicle] = {}
            binaries.gamma[arc][vehicle] = {}

    ensure_vehicle_entry(vehicle_pair.vehicle_one)
    ensure_vehicle_entry(vehicle_pair.vehicle_two)


def create_arc_entry(binaries: Binaries, arc: int) -> None:
    if arc not in binaries.alpha:
        binaries.alpha[arc] = {}
        binaries.beta[arc] = {}
        binaries.gamma[arc] = {}


def process_vehicle_pair(binaries: Binaries, vehicle_pair: VehiclePair) -> None:
    update_alpha(binaries, vehicle_pair)
    update_beta(binaries, vehicle_pair)
    update_gamma(binaries, vehicle_pair)


def get_conflict_binaries(conflicting_sets: list[list[int]], shortest_paths: list[list[int]],
                          congested_schedule: Schedules, print_variables=False) -> Binaries:
    if print_variables:
        print("Computing conflicting binaries ...", end="")

    binaries = Binaries({}, {}, {})
    for arc, conflicting_set in enumerate(conflicting_sets):
        if arc == 0 or not conflicting_set:
            continue

        create_arc_entry(binaries, arc)
        for vehicle_one, vehicle_two in itertools.combinations(conflicting_set, 2):
            position_one = shortest_paths[vehicle_one].index(arc)
            position_two = shortest_paths[vehicle_two].index(arc)

            vehicle_pair = VehiclePair(
                arc=arc,
                vehicle_one=vehicle_one,
                vehicle_two=vehicle_two,
                departure_one=congested_schedule[vehicle_one][position_one],
                arrival_one=congested_schedule[vehicle_one][position_one + 1],
                departure_two=congested_schedule[vehicle_two][position_two],
                arrival_two=congested_schedule[vehicle_two][position_two + 1],
            )

            initialize_binaries(binaries, arc, vehicle_pair)
            process_vehicle_pair(binaries, vehicle_pair)

    number_of_binaries = sum(
        len(binaries.alpha[arc]) * len(binaries.alpha[arc][v1])
        for arc in binaries.alpha for v1 in binaries.alpha[arc]
    ) * 3

    if print_variables:
        print(f"done! The number of binary variables is {number_of_binaries}")

    return binaries


def derive_flows(instance, gammas) -> list[list[int]]:
    flows = []
    for vehicle, path in enumerate(instance.trip_routes):
        vehicle_flows = []
        for arc in path:
            if arc in gammas and vehicle in gammas[arc]:
                flow = sum(gammas[arc][vehicle].values())
            else:
                flow = 0
            vehicle_flows.append(flow)
        flows.append(vehicle_flows)
    return flows
