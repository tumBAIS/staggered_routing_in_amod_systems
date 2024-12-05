from __future__ import annotations

from typing import Optional, Any

Time = float
Staggering = float
NodeID = int
ArcID = int
VehicleID = int
NodesPath = list[NodeID]
OsmInfo = dict[str, Any]
VehicleSchedule = list[Time]
VehicleSchedules = list[list[float]]
UndividedConflictingSets = list[list[list[int]]]
ConflictingSetsAfterPreprocessing = list[list[int]]
