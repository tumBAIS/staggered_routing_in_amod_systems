from typing import Optional, Union

import numpy as np

from utils.aliases import *
from input_data import SPEED_KPH, InstanceParameters


class Arc:

    def __init__(self, id: ArcID, max_flow_allowed: float, osm_info: Optional[OsmInfo] = None, is_dummy: bool = False):
        """
        Initialize an Arc. Use the class method `Arc.create_dummy_arc()` to create dummy arcs.
        """
        self.id = id
        self.is_dummy = is_dummy
        self.precomputed_delays = {}

        if not is_dummy:
            if osm_info is None:
                raise ValueError("osm_info must be provided for non-dummy arcs.")
            self.geometry = osm_info["geometry"]
            self.length = osm_info["length"]
            self.u_original = osm_info["u_original"]
            self.v_original = osm_info["v_original"]
            self.u_v_original = (self.u_original, self.v_original)
            self.nominal_capacity = self.get_nominal_capacity(max_flow_allowed)
        else:
            self.geometry = None
            self.length = 0
            self.nominal_capacity = 0

    @classmethod
    def create_dummy_arc(cls, id: ArcID):
        """Factory method to create a dummy arc."""
        return cls(id=id, is_dummy=True, max_flow_allowed=0)

    @property
    def nominal_travel_time(self):
        if self.is_dummy:
            return 0
        if self.length is None:
            raise AttributeError("Arc length is not set.")
        return self.length * 3.6 / SPEED_KPH

    def __str__(self):
        return f"arc_{self.id}"

    def __repr__(self):
        return f"arc_{self.id}"

    def get_nominal_capacity(self, max_flow_allowed: float) -> int:
        return int(np.ceil(self.nominal_travel_time / max_flow_allowed))
