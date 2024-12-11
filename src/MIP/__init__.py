from __future__ import annotations

import datetime

import gurobipy as grb


class StaggeredRoutingModel(grb.Model):

    def __init__(self, initial_total_delay, start_solution_time):
        super().__init__("staggered_routing")
        # Optimization Metrics
        self._optimize_flag = True
        self._optimalityGap = [100]
        self._lowerBound = [0]
        self._upperBound = [initial_total_delay]
        self._optimizationTime = [self.get_optimization_time(start_solution_time)]
        self._flagUpdate = False
        self._bestLowerBound = 0
        self._bestUpperBound = float("inf")
        self._improvementClock = datetime.datetime.now().timestamp()
        # Info on constraints
        self._numBigMConstraints = 0
        # Variables
        self._alpha = {}
        self._beta = {}
        self._gamma = {}

    def add_conflict_pair_var(self, arc, first_vehicle, second_vehicle, name, lb, ub, var_name):
        conflict_var = {
            "alpha": self._alpha,
            "beta": self._beta,
            "gamma": self._gamma,
        }
        conflict_var[var_name][arc][first_vehicle][second_vehicle] = (
            self.addVar(vtype=grb.GRB.BINARY, name=name, lb=lb, ub=ub, obj=0, column=None)
            if lb != ub else lb)

    def add_arc_conflict_vars(self, arc):
        self._alpha[arc] = {}
        self._beta[arc] = {}
        self._gamma[arc] = {}

    def add_trip_to_arc_conflict_vars(self, arc, first_trip):
        self._alpha[arc][first_trip] = {}
        self._beta[arc][first_trip] = {}
        self._gamma[arc][first_trip] = {}

    def has_trip_conflict_vars_on_arc(self, arc, trip) -> bool:
        return trip in self._alpha[arc]

    @staticmethod
    def get_optimization_time(start_solution_time: float) -> float:
        return datetime.datetime.now().timestamp() - start_solution_time

    def set_optimize_flag(self, arg_flag: bool):
        self._optimize_flag = arg_flag

    def get_optimize_flag(self) -> bool:
        return self._optimize_flag

    def get_last_optimality_gap(self):
        if self._optimalityGap:
            return self._optimalityGap[-1]
        else:
            raise IndexError("no values in self._optimalityGap")

    def store_lower_bound(self):
        self._lowerBound.append(round(self.ObjBound, 2))

    def store_upper_bound(self):
        self._upperBound.append(round(self.getObjective().getValue(), 2))

    def store_optimality_gap(self):
        self._optimalityGap.append(round(self.MIPGap * 100, 2))

    def store_optimization_time(self, start_time: float):
        self._optimizationTime.append(datetime.datetime.now().timestamp() - start_time)

    def get_lower_bound_list(self) -> list[float]:
        return self._lowerBound

    def get_upper_bound_list(self) -> list[float]:
        return self._upperBound

    def get_optimality_gap_list(self) -> list[float]:
        return self._optimalityGap

    def get_optimization_time_list(self) -> list[float]:
        return self._optimizationTime
