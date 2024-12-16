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
VehicleSchedule = list[Time]
TripSchedules = list[list[float]]
UndividedConflictingSets = list[list[list[int]]]
ConflictingSets = list[list[int]]

# Aliases for routes generation.
RoutesFile = list[dict]
