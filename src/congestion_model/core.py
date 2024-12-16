from __future__ import annotations

import cpp_module as cpp
from input_data import SolverParameters
from instance_module.instance import Instance
from instance_module.epoch_instance import EpochInstance
from utils.aliases import *
from input_data import TOLERANCE


def get_free_flow_schedule(instance: Instance | EpochInstance,
                           congested_schedule: list[Schedule]) -> list[Schedule]:
    free_flow_schedule = [[schedule[0]] for schedule in congested_schedule]

    for vehicle, path in enumerate(instance.trip_routes):
        for arc_index, arc in enumerate(path[:-1]):
            departure_time = free_flow_schedule[vehicle][-1] + instance.travel_times_arcs[arc]
            free_flow_schedule[vehicle].append(departure_time)

    return free_flow_schedule


def get_congested_schedule(instance: Instance,
                           release_times: list[float], solver_params: SolverParameters) -> list[Schedule]:
    cpp_instance = cpp.cpp_instance(
        set_of_vehicle_paths=instance.trip_routes,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        list_of_slopes=instance.instance_params.list_of_slopes,
        list_of_thresholds=instance.instance_params.list_of_thresholds,
        parameters=[solver_params.algorithm_time_limit],
        release_times=release_times,
        deadlines=instance.deadlines,
        lb_travel_time=instance.get_lb_travel_time(),
        conflicting_sets=instance.conflicting_sets
    )
    cpp_scheduler = cpp.cpp_scheduler(cpp_instance)
    cpp_solution = cpp_scheduler.construct_solution(release_times)
    schedule = cpp_solution.get_schedule()
    release_times[:] = [schedule[0] for schedule in schedule]
    return schedule


def get_total_delay(free_flow_schedule: list[Schedule], congested_schedule: list[Schedule]) -> float:
    total_delay = sum(
        congested_schedule[vehicle][-1] - congested_schedule[vehicle][0] -
        (free_flow_schedule[vehicle][-1] - free_flow_schedule[vehicle][0])
        for vehicle in range(len(congested_schedule))
    )
    return total_delay


def get_delays_on_arcs(instance: Instance | EpochInstance,
                       congested_schedule: list[Schedule]) -> list[Schedule]:
    delays_on_arcs = [
        [
            congested_schedule[vehicle][position + 1] - congested_schedule[vehicle][position] -
            instance.travel_times_arcs[arc]
            for position, arc in enumerate(path[:-1])
        ]
        for vehicle, path in enumerate(instance.trip_routes)
    ]
    delays_on_arcs = [[0 if abs(element) < TOLERANCE else element for element in delays] + [0] for delays in
                      delays_on_arcs]
    return delays_on_arcs


def get_total_travel_time(vehicle_schedule: list[Schedule]) -> float:
    return sum([schedule[-1] - schedule[0] for schedule in vehicle_schedule])


def get_staggering_applicable(instance: Instance | EpochInstance, staggering_applied: list[float]) -> list[float]:
    return [v_max_staggering_applicable - v_staggering_applied for v_max_staggering_applicable, v_staggering_applied in
            zip(instance.max_staggering_applicable, staggering_applied)]
