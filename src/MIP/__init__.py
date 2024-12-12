from __future__ import annotations
from typing import Optional
from input_data import SolverParameters
import datetime

import gurobipy as grb


class StaggeredRoutingModel(grb.Model):

    def __init__(self, initial_total_delay, solver_params, start_solution_time):
        super().__init__("staggered_routing")
        # Optimization Metrics
        self._optimize_flag = True
        self._optimalityGap = [100.0]
        self._lowerBound = [0.0]
        self._upperBound = [initial_total_delay]
        self._optimizationTime = [self.get_elapsed_time(start_solution_time)]
        self._flagUpdate = False
        self._bestLowerBound = 0
        self._bestUpperBound = float("inf")
        self._improvementClock = datetime.datetime.now().timestamp()
        self._remainingTimeForOptimization = None
        self.set_remaining_time_for_optimization(solver_params, start_solution_time)
        # Info on constraints
        self._numBigMConstraints = 0
        # Variables
        self._alpha = {}
        self._beta = {}
        self._gamma = {}
        self._totalDelay = self.addVar(vtype=grb.GRB.CONTINUOUS, name="total_delay", lb=0, ub=float("inf"), obj=0,
                                       column=None)
        self._departure = {}
        self._delay = {}
        self._load = {}

        # Callback
        self._cbTotalDelay = None
        self._cbReleaseTimes = []
        self._cbStaggeringApplied = []
        self._cbRemainingTimeSlack = []

    def get_cb_release_times(self):
        return self._cbReleaseTimes

    def get_continuous_var_cb(self, vehicle, arc, var_type) -> float:
        # Mapping for variable types
        continuous_var = {
            "departure": self._departure,
            "delay": self._delay,
            "load": self._load,
        }
        if self.is_gurobi_var(continuous_var[var_type][vehicle][arc]):
            return self.cbGetSolution(continuous_var[var_type][vehicle][arc])
        else:
            return continuous_var[var_type][vehicle][arc]

    @staticmethod
    def is_gurobi_var(variable) -> bool:
        return isinstance(variable, grb.Var)

    def add_continuous_var(self, vehicle, arc, lb, ub, var_type, constant_flag: bool = False):
        # Mapping for variable types
        continuous_var = {
            "departure": self._departure,
            "delay": self._delay,
            "load": self._load,
        }

        # Initialize
        if not vehicle in continuous_var[var_type]:
            continuous_var[var_type][vehicle] = {}

        # Validate bounds
        assert lb <= ub + 1e-6, (
            f"Invalid bounds for {var_type}_vehicle_{vehicle}_arc_{arc}: {lb} <= {ub}"
        )

        # Handle constant variable case
        if abs(lb - ub) < 1e-6 and constant_flag:
            continuous_var[var_type][vehicle][arc] = ub
            return

        # Add a continuous variable to the model
        variable = self.addVar(
            vtype=grb.GRB.CONTINUOUS,
            name=f"{var_type}_vehicle_{vehicle}_arc_{arc}",
            lb=lb,
            ub=ub,
            obj=0,
            column=None
        )

        # Store additional attributes
        variable._lb = lb
        variable._ub = ub

        # Update the variable mapping
        continuous_var[var_type][vehicle][arc] = variable

    def get_flag_update(self) -> bool:
        return self._flagUpdate

    def set_flag_update(self, flag):
        self._flagUpdate = flag

    def set_best_lower_bound(self, value: float):
        self._bestLowerBound = value

    def set_best_upper_bound(self, value: float):
        self._bestUpperBound = value

    def get_best_lower_bound(self):
        return self._bestLowerBound

    def get_best_upper_bound(self):
        return self._bestUpperBound

    def get_cb_total_delay(self):
        return self._cbTotalDelay

    def set_cb_total_delay(self, arg_value):
        self._cbTotalDelay = arg_value

    def set_remaining_time_for_optimization(self, solver_params: SolverParameters, start_solution_time) -> None:
        total_optimization_time = solver_params.algorithm_time_limit
        elapsed_time = datetime.datetime.now().timestamp() - start_solution_time
        self._remainingTimeForOptimization = total_optimization_time - elapsed_time

    def get_remaining_time_for_optimization(self) -> float:
        return self._remainingTimeForOptimization

    def add_conflict_pair_var(self, arc, first_vehicle, second_vehicle, name, lb, ub, var_name):
        conflict_var = {
            "alpha": self._alpha,
            "beta": self._beta,
            "gamma": self._gamma,
        }
        conflict_var[var_name][arc][first_vehicle][second_vehicle] = (
            self.addVar(vtype=grb.GRB.BINARY, name=name, lb=lb, ub=ub, obj=0, column=None)
            if lb != ub else lb)
        if isinstance(conflict_var[var_name][arc][first_vehicle][second_vehicle], grb.Var):
            conflict_var[var_name][arc][first_vehicle][second_vehicle]._lb = lb
            conflict_var[var_name][arc][first_vehicle][second_vehicle]._ub = ub

    def get_conflict_pair_var_bound(self, bound: str, arc, first_trip, second_trip, var_name):
        conflict_var = {
            "alpha": self._alpha,
            "beta": self._beta,
            "gamma": self._gamma,
        }
        if isinstance(conflict_var[var_name][arc][first_trip][second_trip], grb.Var):
            if bound == "lb":
                return conflict_var[var_name][arc][first_trip][second_trip]._lb
            elif bound == "ub":
                return conflict_var[var_name][arc][first_trip][second_trip]._ub
            else:
                raise ValueError("undefined case")
        else:
            # variable is constant
            return conflict_var[var_name][arc][first_trip][second_trip]

    def get_conflicting_trips(self, arc, trip) -> list[int]:
        """Return a list of conflicting trips for a given arc and trip."""
        return list(self._gamma.get(arc, {}).get(trip, {}).keys())

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
    def get_elapsed_time(start_solution_time: float) -> float:
        return datetime.datetime.now().timestamp() - start_solution_time

    def set_optimize_flag(self, arg_flag: bool):
        self._optimize_flag = arg_flag

    def get_optimize_flag(self) -> bool:
        return self._optimize_flag

    def get_last_optimality_gap(self):
        if self._optimalityGap:
            return self._optimalityGap[-1]
        else:
            raise IndexError("no gap values")

    def get_last_lower_bound(self):
        if self._lowerBound:
            return self._lowerBound[-1]
        else:
            raise IndexError("no lb values")

    def get_last_upper_bound(self):
        if self._upperBound:
            return self._upperBound[-1]
        else:
            raise IndexError("no ub values")

    def store_lower_bound(self, arg_value: Optional[float] = None):
        if arg_value:
            self._lowerBound.append(round(arg_value, 2))
        else:
            self._lowerBound.append(round(self.ObjBound, 2))

    def store_upper_bound(self, arg_value: Optional[float] = None):
        if arg_value:
            self._upperBound.append(round(arg_value, 2))
        else:
            self._upperBound.append(round(self.getObjective().getValue(), 2))

    def store_optimality_gap(self, arg_value: Optional[float] = None):
        if arg_value:
            self._optimalityGap.append(round(arg_value, 2))
        else:
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
