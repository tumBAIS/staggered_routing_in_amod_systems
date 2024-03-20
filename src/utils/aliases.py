from __future__ import annotations

from typing import Optional

Time = float
Staggering = float
NodeID = int
ArcID = int
VehicleID = int
Path = list[NodeID]
VehicleSchedule = list[Time]
VehicleSchedules = list[list[float]]
UndividedConflictingSets = list[list[list[int]]]
ConflictingSetsAfterPreprocessing = list[list[int]]
