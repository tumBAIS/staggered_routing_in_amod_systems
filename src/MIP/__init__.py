from __future__ import annotations

import itertools
from typing import Optional, Iterator
from input_data import TOLERANCE, CONSTR_TOLERANCE
import numpy as np
from instance_module.instance import Instance
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

    def get_cb_remaining_time_slack(self):
        return self._cbRemainingTimeSlack

    def set_cb_remaining_time_slack(self, remaining_time_slack):
        self._cbRemainingTimeSlack = remaining_time_slack

    def get_cb_staggering_applied(self):
        return self._cbStaggeringApplied

    def set_cb_staggering_applied(self, cb_staggering_applied):
        self._cbStaggeringApplied = cb_staggering_applied

    def get_cb_release_times(self):
        return self._cbReleaseTimes

    def set_cb_release_times(self, release_times: list[float]):
        self._cbReleaseTimes = release_times

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

    def set_continuous_var(self, vehicle, arc, var_type, value_to_set, mode) -> None:
        # Mapping for variable types
        continuous_var = {
            "departure": self._departure,
            "delay": self._delay,
            "load": self._load,
        }

        if mode not in ["start", "cb"]:
            raise ValueError("Mode must be either 'start' or 'cb'")

        if self.is_gurobi_var(continuous_var[var_type][vehicle][arc]):
            if mode == "cb":
                self.cbSetSolution(continuous_var[var_type][vehicle][arc], value_to_set)
            else:
                continuous_var[var_type][vehicle][arc].Start = value_to_set

    def set_conflicting_var(self, first_trip, second_trip, arc, var_type, value_to_set, mode) -> None:
        # Mapping for variable types
        conflict_var = {
            "alpha": self._alpha,
            "beta": self._beta,
            "gamma": self._gamma,
        }
        if mode not in ["start", "cb"]:
            raise ValueError("Mode must be either 'start' or 'cb'")

        if self.is_gurobi_var(conflict_var[var_type][arc][first_trip][second_trip]):
            if mode == "cb":
                self.cbSetSolution(conflict_var[var_type][arc][first_trip][second_trip], value_to_set)
            else:
                conflict_var[var_type][arc][first_trip][second_trip].Start = value_to_set

    def get_list_conflicting_arcs(self) -> list[int]:
        """Return a list of all conflicting arcs."""
        return list(self._gamma)

    def get_arc_conflicting_pairs(self, arc: int) -> Iterator[tuple[int, int]]:
        """Return an iterator of all conflicting trip pairs for a given arc."""
        return itertools.combinations(self._gamma[arc], 2)

    def get_trips_to_track_on_arc(self, arc: int) -> list[int]:
        """Return an iterator of all conflicting trip pairs for a given arc."""
        return list(self._gamma[arc])

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
        if self.is_gurobi_var(conflict_var[var_name][arc][first_vehicle][second_vehicle]):
            conflict_var[var_name][arc][first_vehicle][second_vehicle]._lb = lb
            conflict_var[var_name][arc][first_vehicle][second_vehicle]._ub = ub

    def get_conflict_pair_var_bound(self, bound: str, arc, first_trip, second_trip, var_name):
        conflict_var = {
            "alpha": self._alpha,
            "beta": self._beta,
            "gamma": self._gamma,
        }
        if self.is_gurobi_var(conflict_var[var_name][arc][first_trip][second_trip]):
            if bound == "lb":
                return conflict_var[var_name][arc][first_trip][second_trip]._lb
            elif bound == "ub":
                return conflict_var[var_name][arc][first_trip][second_trip]._ub
            else:
                raise ValueError("undefined case")
        else:
            # variable is constant
            return conflict_var[var_name][arc][first_trip][second_trip]

    def get_continuous_var_bound(self, bound: str, arc, trip, var_name):
        # Mapping for variable types
        continuous_var = {
            "departure": self._departure,
            "delay": self._delay,
            "load": self._load,
        }

        if self.is_gurobi_var(continuous_var[var_name][trip][arc]):
            if bound == "lb":
                return continuous_var[var_name][trip][arc]._lb
            elif bound == "ub":
                return continuous_var[var_name][trip][arc]._ub
            else:
                raise ValueError("undefined case")
        else:
            # variable is constant
            return continuous_var[var_name][trip][arc]

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

    def add_load_constraint(self, trip: int, arc: int) -> None:
        """Add load constraints for a specific vehicle and arc."""
        self.addConstr(self._load[trip][arc] == grb.quicksum(
            self._gamma[arc][trip][conflicting_trip]
            for conflicting_trip in self.get_conflicting_trips(arc, trip)) + 1,
                       name=f"load_constraint_arc_{arc}_vehicle_{trip}"
                       )

    def add_pwl_constraint(self, vehicle, arc, x_axis_values, y_axis_values):
        self.addGenConstrPWL(
            self._load[vehicle][arc], self._delay[vehicle][arc],
            x_axis_values, y_axis_values,
            name=f"piecewise_delay_arc_{arc}_vehicle_{vehicle}"
        )

    def add_alpha_constraints(self, arc: int, v1: int, v2: int) -> None:
        """Add alpha constraints for two vehicles on a given arc."""
        if not self.is_gurobi_var(self._alpha[arc][v1][v2]):
            return
        self._numBigMConstraints += 2
        M1 = int(
            np.ceil(
                self.get_continuous_var_bound("ub", arc, v1, "departure") -
                self.get_continuous_var_bound("lb", arc, v2, "departure") + CONSTR_TOLERANCE + TOLERANCE))
        M2 = int(
            np.ceil(self.get_continuous_var_bound("ub", arc, v2, "departure") -
                    self.get_continuous_var_bound("lb", arc, v1, "departure") + CONSTR_TOLERANCE + TOLERANCE))

        self.addConstr(
            self._departure[v1][arc] - self._departure[v2][arc] + CONSTR_TOLERANCE <= M1 *
            self._alpha[arc][v1][
                v2],
            name=f"alpha_constr_one_arc_{arc}_vehicles_{v1}_{v2}"
        )
        self.addConstr(
            self._departure[v2][arc] - self._departure[v1][arc] + CONSTR_TOLERANCE <= M2 * (
                    1 - self._alpha[arc][v1][v2]),
            name=f"alpha_constr_two_arc_{arc}_vehicles_{v1}_{v2}"
        )

    def add_alpha_constraints_indicators(self, arc: int, v1: int, v2: int) -> None:
        """Add alpha constraints for two vehicles on a given arc."""
        if not self.is_gurobi_var(self._alpha[arc][v1][v2]):
            return

        self._numBigMConstraints += 2

        self.addGenConstrIndicator(
            self._alpha[arc][v1][v2], True,
            self._departure[v1][arc] - self._departure[v2][arc] - CONSTR_TOLERANCE,
            grb.GRB.GREATER_EQUAL, 0,
            name=f"alpha_constr_one_arc_{arc}_vehicles_{v1}_{v2}"
        )
        self.addGenConstrIndicator(
            self._alpha[arc][v1][v2], False,
            self._departure[v1][arc] - self._departure[v2][arc] + CONSTR_TOLERANCE,
            grb.GRB.LESS_EQUAL, 0,
            name=f"alpha_constr_two_arc_{arc}_vehicles_{v1}_{v2}"
        )

    def add_beta_constraints(self, arc: int, first_vehicle: int, second_vehicle: int,
                             second_vehicle_path: list[int], arc_travel_time: float) -> None:
        """Add beta constraints for two vehicles on a specific arc."""
        if not self.is_gurobi_var(self._beta[arc][first_vehicle][second_vehicle]):
            return
        # Get the index of the current arc and the next arc in the path of the second vehicle
        idx_second_vehicle_path = second_vehicle_path.index(arc)
        next_arc_second_vehicle = second_vehicle_path[idx_second_vehicle_path + 1]

        # Increment the count of Big-M constraints
        self._numBigMConstraints += 2

        # use BIG-M constraints
        M3 = int(np.ceil(
            self.get_continuous_var_bound("ub", next_arc_second_vehicle, second_vehicle, "departure")
            - self.get_continuous_var_bound("lb", arc, first_vehicle, "departure")
            + CONSTR_TOLERANCE + TOLERANCE))
        M4 = int(np.ceil(
            self.get_continuous_var_bound("ub", arc, first_vehicle, "departure") -
            self.get_continuous_var_bound("lb", arc, second_vehicle,
                                          "departure") - arc_travel_time + CONSTR_TOLERANCE + TOLERANCE))

        # Add Big-M constraints
        self.addConstr(
            self._departure[second_vehicle][next_arc_second_vehicle]
            - self._departure[first_vehicle][arc] + CONSTR_TOLERANCE
            <= M3 * self._beta[arc][first_vehicle][second_vehicle],
            name=f"beta_to_zero_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
        )
        self.addConstr(
            self._departure[first_vehicle][arc]
            - self._departure[second_vehicle][next_arc_second_vehicle] + CONSTR_TOLERANCE
            <= M4 * (1 - self._beta[arc][first_vehicle][second_vehicle]),
            name=f"beta_to_one_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
        )

    def add_beta_constraints_indicators(self, arc: int, first_vehicle: int, second_vehicle: int,
                                        second_vehicle_path: list[int]) -> None:
        """Add beta constraints for two vehicles on a specific arc."""
        if not self.is_gurobi_var(self._beta[arc][first_vehicle][second_vehicle]):
            return
        # Get the index of the current arc and the next arc in the path of the second vehicle
        idx_second_vehicle_path = second_vehicle_path.index(arc)
        next_arc_second_vehicle = second_vehicle_path[idx_second_vehicle_path + 1]

        # Increment the count of Big-M constraints
        self._numBigMConstraints += 2

        # Add indicator constraints
        self.addGenConstrIndicator(
            self._beta[arc][first_vehicle][second_vehicle], False,
            self._departure[second_vehicle][next_arc_second_vehicle] + CONSTR_TOLERANCE
            - self._departure[first_vehicle][arc],
            grb.GRB.LESS_EQUAL, 0,
            name=f"beta_to_zero_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
        )
        self.addGenConstrIndicator(
            self._beta[arc][first_vehicle][second_vehicle], True,
            self._departure[second_vehicle][next_arc_second_vehicle] - CONSTR_TOLERANCE
            - self._departure[first_vehicle][arc],
            grb.GRB.GREATER_EQUAL, 0,
            name=f"beta_to_one_{arc}_vehicles_{first_vehicle}_{second_vehicle}"
        )

    def add_gamma_constraints(self, arc: int, v1: int, v2: int) -> None:
        """Add gamma constraints for two vehicles on a given arc."""
        if self.is_gurobi_var(self._gamma[arc][v1][v2]):
            self._numBigMConstraints += 2
            self.addConstr(
                self._gamma[arc][v1][v2] >= self._alpha[arc][v1][v2] + self._beta[arc][v1][v2] - 1,
                name=f"gamma_1_constr_arc_{arc}_vehicles_{v1}_{v2}"
            )
            self.addConstr(
                self._gamma[arc][v1][v2] <= (self._alpha[arc][v1][v2] + self._beta[arc][v1][v2]) / 2,
                name=f"gamma_2_constr_arc_{arc}_vehicles_{v1}_{v2}"
            )

    def add_travel_continuity_constraints(self, instance: Instance) -> None:
        """Add travel continuity constraints to the self."""
        print("Adding travel continuity constraints...")

        for vehicle in self._departure:
            for position in range(1, len(self._departure[vehicle])):
                current_arc = instance.trip_routes[vehicle][position]
                prev_arc = instance.trip_routes[vehicle][position - 1]

                self.addConstr(
                    self._departure[vehicle][current_arc] - self._departure[vehicle][prev_arc] -
                    self._delay[vehicle][prev_arc] == instance.travel_times_arcs[prev_arc],
                    name=f"continuity_vehicle_{vehicle}_arc_{current_arc}"
                )

    def add_objective_function(self) -> None:
        """Set the objective function for minimizing total delay."""
        print("Setting the objective function...")
        self.addConstr(
            self._totalDelay == grb.quicksum(
                self._delay[vehicle][arc] for vehicle in self._delay for arc in self._delay[vehicle]
            ),
            name="total_delay_constraint"
        )
        self.setObjective(self._totalDelay, grb.GRB.MINIMIZE)
        print("Objective: Minimization of total delay.")

    def trip_can_have_delay_on_arc(self, trip, arc) -> bool:
        return isinstance(self._load[trip][arc], grb.Var)

    def print_num_big_m_constraints(self):
        print(f"Number of BigM constraints in model: {self._numBigMConstraints}")
