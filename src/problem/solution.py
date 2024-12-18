from __future__ import annotations

from dataclasses import dataclass, field

from gurobipy import Model
from typing import Optional
from utils.aliases import *
from input_data import TOLERANCE


class Binaries:
    def __init__(self, alpha: dict[int:dict[int:dict[int:int]]],
                 beta: dict[int:dict[int:dict[int:int]]],
                 gamma: dict[int:dict[int:dict[int:int]]]):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma


@dataclass
class Solution:
    delays_on_arcs: list[list[float]]
    free_flow_schedule: list[list[float]]
    congested_schedule: list[list[float]]
    release_times: list[float]
    total_delay: float
    total_travel_time: float
    vehicles_utilizing_arcs: Optional[list[list[int]]] = None
    binaries: Optional[Binaries] = None  # type: ignore
    nothing_to_optimize: bool = False

    def remove_trip(self, trip):
        self.release_times.pop(trip)
        self.congested_schedule.pop(trip)
        assert sum(self.delays_on_arcs[trip]) < TOLERANCE, "Vehicle has non-zero delays on arcs."
        self.delays_on_arcs.pop(trip)
        self.free_flow_schedule.pop(trip)

    def remove_trip_at_position_entry_from_solution(self, trip, position):
        """ Used during simplification: removes entries where delay cannot occur """
        self.congested_schedule[trip].pop(position)
        self.free_flow_schedule[trip].pop(position)
        assert self.delays_on_arcs[trip][position] < TOLERANCE, "Vehicle has delay on the first arc."
        self.delays_on_arcs[trip].pop(position)
        if self.congested_schedule[trip]:
            self.release_times[trip] = self.congested_schedule[trip][0]

    def remove_trip_arcs_between_indices(self, vehicle, start_idx, end_idx):
        del self.congested_schedule[vehicle][start_idx + 1:end_idx + 1]
        del self.free_flow_schedule[vehicle][start_idx + 1:end_idx + 1]
        del self.delays_on_arcs[vehicle][start_idx + 1:end_idx + 1]

    def print_congestion_info(self) -> None:
        """
        Print summary statistics about the congestion in the simplified system.
        """
        total_free_flow_time = self.total_travel_time - self.total_delay
        congestion_delay_percentage = (self.total_delay / self.total_travel_time) * 100
        tomtom_congestion_index = ((self.total_travel_time - total_free_flow_time) / total_free_flow_time) * 100

        print("\n--- Congestion Information Summary ---")
        print(f"Total Travel Time:         {self.total_travel_time:.2f} [sec]")
        print(f"Total Delay:               {self.total_delay:.2f} [sec]")
        print(f"Free Flow Travel Time:     {total_free_flow_time:.2f} [sec]")
        print(f"Congestion Delay:          {congestion_delay_percentage:.2f}% of travel time")
        print(f"TomTom Congestion Index:   {tomtom_congestion_index:.2f}%")
        print("--------------------------------------")


@dataclass
class HeuristicSolution:
    congested_schedule: Schedules
    binaries: Binaries
    delays_on_arcs: Schedules
    total_delay: float
