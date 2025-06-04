from __future__ import annotations

import dataclasses
import datetime
import statistics

from dataclasses import dataclass

from typing import Optional
from utils.aliases import *
from input_data import TOLERANCE, SolverParameters


class Binaries:
    def __init__(self, alpha: ConflictVarsDict,
                 beta: ConflictVarsDict,
                 gamma: ConflictVarsDict):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma


def _format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs}s"


@dataclass
class Solution:
    delays_on_arcs: list[list[float]]
    congested_schedule: list[list[float]]
    start_times: list[float]
    total_delay: float
    total_travel_time: float
    total_delay_on_arcs: list[float] = dataclasses.field(default_factory=list)
    binaries: Optional[Binaries] = None  # type: ignore

    @classmethod
    def from_cpp_solution(cls, cpp_solution, cpp_instance):
        obj = cls(
            delays_on_arcs=cpp_solution.get_delays_on_arcs(cpp_instance),
            start_times=cpp_solution.get_start_times(),
            total_delay=cpp_solution.get_total_delay(),
            congested_schedule=cpp_solution.get_schedule(),
            total_travel_time=cpp_solution.get_total_travel_time(),
            binaries=None,
        )

        routes = cpp_instance.get_trip_routes()  # list[list[int]]
        num_arcs = cpp_instance.get_number_of_arcs()
        obj.total_delay_on_arcs = [0.0 for _ in range(num_arcs)]

        for trip_delay_list, arc_route in zip(obj.delays_on_arcs, routes):
            for arc_id, delay in zip(arc_route, trip_delay_list):
                obj.total_delay_on_arcs[arc_id] += delay

        return obj

    def remove_trip(self, trip):
        self.start_times.pop(trip)
        self.congested_schedule.pop(trip)
        assert sum(self.delays_on_arcs[trip]) < TOLERANCE, "Vehicle has non-zero delays on arcs."
        self.delays_on_arcs.pop(trip)

    def remove_trip_at_position_entry_from_solution(self, trip, position):
        """ Used during simplification: removes entries where delay cannot occur """
        self.congested_schedule[trip].pop(position)
        assert self.delays_on_arcs[trip][position] < TOLERANCE, "Vehicle has delay on the first arc."
        self.delays_on_arcs[trip].pop(position)
        if self.congested_schedule[trip]:
            self.start_times[trip] = self.congested_schedule[trip][0]

    def remove_trip_arcs_between_indices(self, vehicle, start_idx, end_idx):
        del self.congested_schedule[vehicle][start_idx + 1:end_idx + 1]
        del self.delays_on_arcs[vehicle][start_idx + 1:end_idx + 1]

    def print_congestion_info(self) -> None:
        """
        Print summary statistics about the congestion in the simplified system.
        """
        total_free_flow_time = self.total_travel_time - self.total_delay
        congestion_delay_percentage = (self.total_delay / self.total_travel_time) * 100
        tomtom_congestion_index = ((self.total_travel_time - total_free_flow_time) / total_free_flow_time) * 100

        print("\n--- Congestion Information Summary ---")
        print(f"Total Travel Time:         {_format_seconds(self.total_travel_time)}")
        print(f"Total Delay:               {_format_seconds(self.total_delay)}")
        print(f"Free Flow Travel Time:     {_format_seconds(total_free_flow_time)}")
        print(f"Congestion Delay:          {congestion_delay_percentage:.2f}% of travel time")
        print(f"TomTom Congestion Index:   {tomtom_congestion_index:.2f}%")
        print("--------------------------------------")

    def print_delay_distributions(self) -> None:
        """
        Print statistical summaries of delay distributions.
        """
        if not self.delays_on_arcs:
            print("[WARN]: delays on arcs not set, therefore won't print.")
            return

        trip_total_delays = [sum(trip) for trip in self.delays_on_arcs]
        all_individual_delays = [d for trip in self.delays_on_arcs for d in trip]

        def describe(data, label):
            if not data:
                print(f"No data for {label}")
                return

            def quantile(q):
                return _format_seconds(statistics.quantiles(data, n=100)[q - 1])

            print(f"\n--- {label} ---")
            print(f"Min:        {_format_seconds(min(data))}")
            print(f"10th perc:  {quantile(10)}")
            print(f"25th perc:  {quantile(25)}")
            print(f"Median:     {_format_seconds(statistics.median(data))}")
            print(f"75th perc:  {quantile(75)}")
            print(f"90th perc:  {quantile(90)}")
            print(f"Max:        {_format_seconds(max(data))}")
            print(f"Mean:       {_format_seconds(statistics.mean(data))}")
            if len(data) > 1:
                print(f"Std Dev:    {_format_seconds(statistics.stdev(data))}")
            else:
                print("Std Dev:    N/A")

        describe(trip_total_delays, "Total Delay per Trip")
        describe(all_individual_delays, "Individual Delay Values")
        describe(self.total_delay_on_arcs, "Total Delay per Arc")

    from problem.epoch_instance import EpochInstance  # avoids circular improts
    def get_map_previous_epoch_trips_to_start_time(self, instance: EpochInstance, solver_params: SolverParameters,
                                                   epoch_id) -> (
            dict[int:float]):
        """Look at the congested schedule and everyone whose schedule goes into new epoch, you return it"""
        start_time_next_epoch = solver_params.epoch_size * 60 * (epoch_id + 1)
        map_previous_epoch_trips_to_start_time = dict()
        for trip, schedule in enumerate(self.congested_schedule):
            if schedule[-1] > start_time_next_epoch:
                map_previous_epoch_trips_to_start_time[instance.get_trip_original_id(trip)] = schedule[0]

        return map_previous_epoch_trips_to_start_time
