from __future__ import annotations

import cpp_module as cpp
from instanceModule.instance import Instance
from instanceModule.epoch_instance import EpochInstance
from utils.aliases import *


def get_free_flow_schedule(instance: Instance | EpochInstance,
                           congestedSchedule: list[VehicleSchedule]) -> list[VehicleSchedule]:
    freeFlowSchedule = [[schedule[0]] for schedule in congestedSchedule]

    for vehicle, path in enumerate(instance.trip_routes):
        for arcIndex, arc in enumerate(path[:-1]):
            departureTime = freeFlowSchedule[vehicle][-1] + instance.travel_times_arcs[arc]
            freeFlowSchedule[vehicle].append(departureTime)

    return freeFlowSchedule


def get_congested_schedule(instance: Instance | EpochInstance,
                           release_times: list[float]) -> list[VehicleSchedule]:
    cpp_parameters = [instance.input_data.algorithm_time_limit]
    cpp_instance = cpp.cpp_instance(
        set_of_vehicle_paths=instance.trip_routes,
        travel_times_arcs=instance.travel_times_arcs,
        capacities_arcs=instance.capacities_arcs,
        list_of_slopes=instance.input_data.list_of_slopes,
        list_of_thresholds=instance.input_data.list_of_thresholds,
        parameters=cpp_parameters,
        release_times=release_times,
        lb_travel_time=instance.get_lb_travel_time()
    )
    cpp_scheduler = cpp.cpp_scheduler(cpp_instance)
    cpp_solution = cpp_scheduler.construct_solution(release_times)
    schedule = cpp_solution.get_schedule()
    release_times[:] = [schedule[0] for schedule in schedule]
    return schedule


def get_total_delay(freeFlowSchedule: list[VehicleSchedule], congestedSchedule: list[VehicleSchedule]) -> float:
    totalDelay = sum(congestedSchedule[vehicle][-1] - congestedSchedule[vehicle][0] -
                     (freeFlowSchedule[vehicle][-1] - freeFlowSchedule[vehicle][0])
                     for vehicle in range(len(congestedSchedule)))
    return totalDelay


def get_delays_on_arcs(instance: Instance | EpochInstance,
                       congestedSchedule: list[VehicleSchedule]) -> list[VehicleSchedule]:
    delaysOnArcs = [
        [
            congestedSchedule[vehicle][position + 1] - congestedSchedule[vehicle][position] -
            instance.travel_times_arcs[arc]
            for position, arc in enumerate(path[:-1])
        ]
        for vehicle, path in enumerate(instance.trip_routes)
    ]
    delaysOnArcs = [[0 if abs(element) < 1e-6 else element for element in delays] + [0] for delays in delaysOnArcs]
    return delaysOnArcs


def get_total_travel_time(vehicleSchedule: list[VehicleSchedule]) -> float:
    return sum([schedule[-1] - schedule[0] for schedule in vehicleSchedule])


def get_staggering_applicable(instance: Instance | EpochInstance, staggeringApplied: list[float]):
    return [vMaxStaggeringApplicable - vStaggeringApplied for vMaxStaggeringApplicable, vStaggeringApplied in
            zip(instance.max_staggering_applicable, staggeringApplied)]
