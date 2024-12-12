from __future__ import annotations

from dataclasses import dataclass, field

from gurobipy import Model
from typing import Optional
from utils.aliases import *


class Binaries:
    def __init__(self, alpha: dict[int:dict[int:dict[int:int]]],
                 beta: dict[int:dict[int:dict[int:int]]],
                 gamma: dict[int:dict[int:dict[int:int]]]):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma


@dataclass
class EpochSolution:
    delays_on_arcs: list[list[float]]
    free_flow_schedule: list[list[float]]
    congested_schedule: list[list[float]]
    release_times: list[float]
    staggering_applicable: list[float]
    staggering_applied: list[float]
    vehicles_utilizing_arcs: list[list[int]]
    total_delay: float
    total_travel_time: float
    nothing_to_optimize: bool = False
    binaries: Binaries = field(default=Binaries)


@dataclass
class CompleteSolution:
    delays_on_arcs: list[list[float]]
    free_flow_schedule: list[list[float]]
    congested_schedule: list[list[float]]
    release_times: list[float]
    staggering_applicable: list[float]
    staggering_applied: list[float]
    total_delay: float
    total_travel_time: float
    binaries: Optional[Binaries]  # type: ignore
    nothing_to_optimize: bool = False


@dataclass(init=False)
class OptimizationMeasures:
    upper_bound: list[float] = field(default_factory=list[float])
    lower_bound: list[float] = field(default_factory=list[float])
    optimization_time: list[float] = field(default_factory=list[float])
    optimality_gap: list[float] = field(default_factory=list[float])
    measure_exist: bool = False

    def __init__(self, model: Model):
        try:
            self.upper_bound = model._upperBound
            self.lower_bound = model._lowerBound
            self.optimization_time = model._optimizationTime
            self.optimality_gap = model._optimalityGap
            self.measure_exist = True
        except AttributeError:
            print("optimization measures not collected because not found in model")


@dataclass
class HeuristicSolution:
    congested_schedule: TripSchedules
    binaries: Binaries
    delays_on_arcs: TripSchedules
    total_delay: float
