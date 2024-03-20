from __future__ import annotations

from dataclasses import dataclass, field

from gurobipy import Model
from typing import Optional
from utils.aliases import VehicleSchedules


class Binaries:
    def __init__(self, alpha: dict[int:dict[int:dict[int:int]]],
                 beta: dict[int:dict[int:dict[int:int]]],
                 gamma: dict[int:dict[int:dict[int:int]]]):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma


@dataclass
class EpochSolution:
    delaysOnArcs: list[list[float]]
    freeFlowSchedule: list[list[float]]
    congestedSchedule: list[list[float]]
    releaseTimes: list[float]
    staggeringApplicable: list[float]
    staggeringApplied: list[float]
    vehiclesUtilizingArcs: list[list[int]]
    totalDelay: float
    totalTravelTime: float
    nothingToOptimize: bool = False
    binaries: Binaries = field(default=Binaries)


@dataclass
class CompleteSolution:
    delaysOnArcs: list[list[float]]
    freeFlowSchedule: list[list[float]]
    releaseTimes: list[float]
    staggeringApplicable: list[float]
    staggeringApplied: list[float]
    totalDelay: float
    totalTravelTime: float
    congestedSchedule: list[list[float]]
    binaries: Optional[Binaries]  # type: ignore
    nothingToOptimize: bool = False


@dataclass(init=False)
class OptimizationMeasures:
    upperBound: list[float] = field(default_factory=list[float])
    lowerBound: list[float] = field(default_factory=list[float])
    optimizationTime: list[float] = field(default_factory=list[float])
    optimalityGap: list[float] = field(default_factory=list[float])
    measureExist: bool = False

    def __init__(self, model: Model):
        try:
            self.upperBound = model._upperBound
            self.lowerBound = model._lowerBound
            self.optimizationTime = model._optimizationTime
            self.optimalityGap = model._optimalityGap
            self.measureExist = True
        except AttributeError:
            print("optimization measures not collected because not found in model")


@dataclass
class HeuristicSolution:
    congestedSchedule: VehicleSchedules
    binaries: Binaries
    delaysOnArcs: VehicleSchedules
    totalDelay: float
