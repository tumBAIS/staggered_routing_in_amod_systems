#include <iostream>
#include <cmath>
#include <queue>
#include <cassert>
#include <chrono>
#include "scheduler.h"
#include "conflict_searcher.h"

namespace cpp_module {

// Stagger a trip by adjusting its start time and related metrics
    auto stagger_trip(Solution &solution, long vehicle, double staggering) -> void {
        solution.increase_trip_start_time(vehicle, staggering);
        solution.increase_staggering_applied(vehicle, staggering);
        solution.increase_remaining_time_slack(vehicle, -staggering);
    }

// Check if the maximum time limit for the optimization process is reached
    auto check_time_limit_reached(double start_time, double max_optimization_time) -> bool {
        double current_time = clock() / static_cast<double>(CLOCKS_PER_SEC);
        double elapsed_time = current_time - start_time;

        if (elapsed_time > max_optimization_time) {
            std::cout << "STOPPING LOCAL SEARCH - MAX TIME LIMIT REACHED\n";
            return true;
        }
        return false;
    }

// Reset a new solution to match the current solution and clear conflicts
    auto reset_solution(Solution &new_solution, const Solution &current_solution, Conflict &conflict) -> void {
        stagger_trip(new_solution, conflict.current_trip_id, -conflict.staggeringCurrentVehicle);
        conflict.staggeringCurrentVehicle = 0;
        stagger_trip(new_solution, conflict.other_trip_id, conflict.destaggeringOtherVehicle);
        conflict.destaggeringOtherVehicle = 0;

        new_solution.set_schedule(current_solution.get_schedule());
        new_solution.set_total_delay(current_solution.get_total_delay());
        new_solution.set_ties_flag(current_solution.get_ties_flag());
        new_solution.set_feasible_and_improving_flag(current_solution.get_feasible_and_improving_flag());
    }

// Apply staggering to resolve a conflict
    auto resolve_conflict(Solution &solution, Conflict &conflict) -> void {
        assert(conflict.distanceToCover > 0);

        bool can_move_current_only =
                conflict.distanceToCover < solution.get_trip_remaining_time_slack(conflict.current_trip_id);

        bool can_move_both =
                conflict.distanceToCover <
                solution.get_trip_remaining_time_slack(conflict.current_trip_id) +
                solution.get_trip_staggering_applied(conflict.other_trip_id);

        if (can_move_current_only) {
            stagger_trip(solution, conflict.current_trip_id, conflict.distanceToCover);
            conflict.staggeringCurrentVehicle += conflict.distanceToCover;
        } else if (can_move_both) {
            double staggering = std::max(0.0, solution.get_trip_remaining_time_slack(conflict.current_trip_id));
            double destaggering = conflict.distanceToCover - staggering;

            stagger_trip(solution, conflict.current_trip_id, staggering);
            stagger_trip(solution, conflict.other_trip_id, -destaggering);

            conflict.staggeringCurrentVehicle += staggering;
            conflict.destaggeringOtherVehicle += destaggering;
        } else {
            throw std::invalid_argument("Unable to resolve conflict: insufficient slack.");
        }
    }

// Update the current solution with changes from a resolved conflict
    auto update_solution(Solution &current_solution, const Solution &new_solution, Conflict &conflict) -> void {
        stagger_trip(current_solution, conflict.current_trip_id, conflict.staggeringCurrentVehicle);
        stagger_trip(current_solution, conflict.other_trip_id, -conflict.destaggeringOtherVehicle);

        current_solution.set_schedule(new_solution.get_schedule());
        current_solution.set_total_delay(new_solution.get_total_delay());
        current_solution.set_ties_flag(new_solution.get_ties_flag());
        current_solution.set_feasible_and_improving_flag(new_solution.get_feasible_and_improving_flag());
    }

// Print details of a move made during conflict resolution
    auto print_move(const Solution &old_solution, const Solution &new_solution, const Conflict &conflict) -> void {
        if (std::abs(old_solution.get_total_delay() - new_solution.get_total_delay()) > TOLERANCE) {
            if (conflict.staggeringCurrentVehicle > 0) {
                std::cout << " - Staggering " << conflict.current_trip_id << " by "
                          << conflict.staggeringCurrentVehicle;
            }
            if (conflict.destaggeringOtherVehicle > 0) {
                std::cout << " - Destaggering " << conflict.other_trip_id << " by "
                          << conflict.destaggeringOtherVehicle;
            }
            std::cout << " - New Delay: " << new_solution.get_total_delay()
                      << " -> Reduction: "
                      << old_solution.get_total_delay() - new_solution.get_total_delay() << "\n";
        }
    }

// Update the distance required to resolve a conflict
    auto update_distance_to_cover(const Solution &solution, Conflict &conflict, const Instance &instance) -> void {
        auto current_index = get_index(instance.get_trip_route(conflict.current_trip_id), conflict.arc);
        auto other_index = get_index(instance.get_trip_route(conflict.other_trip_id), conflict.arc);

        conflict.distanceToCover =
                solution.get_trip_arc_departure(conflict.other_trip_id, other_index + 1) -
                solution.get_trip_arc_departure(conflict.current_trip_id, current_index) - CONSTR_TOLERANCE;
    }

// Check if it is possible to resolve a conflict
    auto can_resolve_conflict(double distance_to_cover, double current_slack, double other_staggering) -> bool {
        return (current_slack + other_staggering) > distance_to_cover;
    }

// Check if a solution is admissible
    auto is_solution_admissible(Solution &solution, Scheduler &scheduler) -> bool {
        if (!solution.get_feasible_and_improving_flag()) {
            return false;
        }
        if (solution.get_ties_flag()) {
            scheduler.solution_with_ties++;
            return false;
        }
        return true;
    }

// Resolve a conflict by applying staggering or destaggering
    auto
    solve_conflict(Conflict &conflict, Solution &solution, const Instance &instance, Scheduler &scheduler) -> void {
        scheduler.explored_solutions++;
        while (conflict.distanceToCover > CONSTR_TOLERANCE) {
            if (check_time_limit_reached(scheduler.start_search_clock, instance.get_max_time_optimization())) {
                break;
            }

            bool has_slack = can_resolve_conflict(
                    conflict.distanceToCover,
                    solution.get_trip_remaining_time_slack(conflict.current_trip_id),
                    solution.get_trip_staggering_applied(conflict.other_trip_id)
            );

            if (!has_slack) {
                scheduler.slack_not_enough++;
                break;
            }

            resolve_conflict(solution, conflict);
            scheduler.update_existing_congested_schedule(solution, conflict);

            if (!solution.get_feasible_and_improving_flag()) {
                break;
            }

            update_distance_to_cover(solution, conflict, instance);
        }
    }

// Attempt to improve a solution by resolving conflicts
    auto improve_solution(const Instance &instance, const std::vector<Conflict> &conflicts, Scheduler &scheduler,
                          Solution &solution) -> bool {
        Solution new_solution(solution);

        for (auto conflict: conflicts) {
            if (std::abs(conflict.distanceToCover) < 1e-6) {
                continue;
            }

            solve_conflict(conflict, new_solution, instance, scheduler);

            if (check_time_limit_reached(scheduler.start_search_clock, instance.get_max_time_optimization())) {
                return false;
            }

            if (is_solution_admissible(new_solution, scheduler)) {
                print_move(solution, new_solution, conflict);
                update_solution(solution, new_solution, conflict);
                return true;
            } else {
                reset_solution(new_solution, solution, conflict);
            }
        }

        return false;
    }

// Improve the solution by iteratively resolving conflicts
    auto improve_towards_solution_quality(const Instance &instance, Solution &solution, Scheduler &scheduler) -> void {
        ConflictSearcherNew conflict_searcher(instance);

        while (true) {
            if (check_time_limit_reached(scheduler.start_search_clock, instance.get_max_time_optimization())) {
                break;
            }

            scheduler.best_total_delay = solution.get_total_delay();
            auto conflicts = conflict_searcher.get_conflicts_list(solution.get_schedule());
            sort_conflicts(conflicts);

            if (conflicts.empty()) {
                break;
            }

            if (!improve_solution(instance, conflicts, scheduler, solution)) {
                break;
            }
        }

        scheduler.construct_schedule(solution);
    }

} // namespace cpp_module
