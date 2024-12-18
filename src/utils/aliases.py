from __future__ import annotations

from typing import Any

Time = float
Staggering = float
NodeID = int
ArcID = int
VehicleID = int
NodesPath = list[NodeID]
RelabeledNodesArcID = (NodeID, NodeID)
OsmInfo = dict[str, Any]
Schedule = list[Time]
Schedules = list[Schedule]
UndividedConflictingSets = list[list[list[int]]]
ConflictingSets = list[list[int]]
OptimizationMeasures = dict[str, list[float]]
ConflictVarsDict = dict[int:dict[int:dict[int:int]]]
# Aliases for routes generation.
RoutesFile = list[dict]
