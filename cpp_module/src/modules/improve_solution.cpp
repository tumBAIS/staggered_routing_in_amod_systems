#include <iostream>
#include <iomanip>
#include <cmath>
#include "scheduler.h"
#include "conflict_searcher.h"
#include <queue>
#include <cassert>
#include <chrono>

namespace cpp_module {
    
    auto check_if_time_limit_is_reached(const double start_search_clock, double max_time_optimization) -> bool {
        auto time_now = clock() / (double) CLOCKS_PER_SEC;
        auto duration = (time_now - start_search_clock);
        if (duration > max_time_optimization) {
            std::cout << "STOPPING LOCAL SEARCH - MAX TIME LIMIT REACHED \n";
            return true;
        }
        return false;
    }

    auto reset_new_solution(const Solution &current_solution, Solution &new_solution,
                            Conflict &conflict) -> void {
        new_solution.increase_trip_start_time(conflict.current_trip_id, -conflict.staggering_current_vehicle);
        conflict.staggering_current_vehicle = 0;
        new_solution.increase_trip_start_time(conflict.other_trip_id, conflict.destaggering_other_vehicle);
        conflict.destaggering_other_vehicle = 0;
        new_solution.set_schedule(current_solution.get_schedule());
        new_solution.set_total_delay(current_solution.get_total_delay());
        new_solution.set_ties_flag(current_solution.get_ties_flag());
        new_solution.set_feasible_and_improving_flag(current_solution.get_feasible_and_improving_flag());
    }

    auto Scheduler::apply_staggering_to_solve_conflict(Solution &complete_solution,
                                                       Conflict &conflict) const -> void {
        assert(conflict.distance_to_cover > 0);
        bool move_vehicle_one =
                conflict.distance_to_cover < get_trip_remaining_time_slack(complete_solution, conflict.current_trip_id);
        bool move_both_vehicles =
                conflict.distance_to_cover <
                get_trip_remaining_time_slack(complete_solution, conflict.current_trip_id) +
                get_trip_staggering_applied(complete_solution, conflict.other_trip_id);
        if (move_vehicle_one) {
            complete_solution.increase_trip_start_time(conflict.current_trip_id, conflict.distance_to_cover);
            conflict.staggering_current_vehicle += conflict.distance_to_cover;
            assert(conflict.distance_to_cover > 0);
        } else if (move_both_vehicles) {
            // Distance can be covered removing staggering to other vehicle
            auto staggering = std::max(0.0, get_trip_remaining_time_slack(complete_solution, conflict.current_trip_id));
            auto destaggering = conflict.distance_to_cover - staggering;
            complete_solution.increase_trip_start_time(conflict.current_trip_id, staggering);
            complete_solution.increase_trip_start_time(conflict.other_trip_id, -destaggering);
            conflict.staggering_current_vehicle += staggering;
            conflict.destaggering_other_vehicle += destaggering;
            assert(staggering > 0 || destaggering > 0);
        } else {
            throw std::invalid_argument("Applying staggering to solve conflict - undefined case");
        }
    }

    auto update_current_solution(Solution &current_solution,
                                 const Solution &new_solution,
                                 Conflict &conflict) -> void {
        // Update current vehicle
        current_solution.increase_trip_start_time(conflict.current_trip_id, conflict.staggering_current_vehicle);
        current_solution.increase_trip_start_time(conflict.other_trip_id, -conflict.destaggering_other_vehicle);
        current_solution.set_schedule(new_solution.get_schedule());
        current_solution.set_total_delay(new_solution.get_total_delay());
        current_solution.set_ties_flag(new_solution.get_ties_flag());
        current_solution.set_feasible_and_improving_flag(new_solution.get_feasible_and_improving_flag());
    }

    auto print_move(const Solution &old_solution,
                    const Solution &new_solution,
                    const Conflict &conflict) -> void {
        if (std::abs(old_solution.get_total_delay() - new_solution.get_total_delay()) > TOLERANCE) {
            std::ostringstream output;

            if (conflict.staggering_current_vehicle > 0) {
                output << "Staggering trip " << conflict.current_trip_id
                       << " by " << std::fixed << std::setprecision(2)
                       << conflict.staggering_current_vehicle << "; ";
            }

            if (conflict.destaggering_other_vehicle > 0) {
                output << "destaggering trip " << conflict.other_trip_id
                       << " by " << std::fixed << std::setprecision(2)
                       << conflict.destaggering_other_vehicle << "; ";
            }

            output << "new total delay: " << std::fixed << std::setprecision(2)
                   << new_solution.get_total_delay()
                   << "; delay improvement: "
                   << old_solution.get_total_delay() - new_solution.get_total_delay();

            std::cout << output.str() << std::endl;
        }
    }


    auto update_distance_to_cover(const Solution &complete_solution,
                                  Conflict &conflict,
                                  const Instance &instance) -> void {
        auto index_arc_in_path_current_vehicle = get_index(instance.get_trip_route(conflict.current_trip_id),
                                                           conflict.arc);
        auto index_arc_in_path_other_vehicle = get_index(instance.get_trip_route(conflict.other_trip_id), conflict.arc);

        conflict.distance_to_cover =
                complete_solution.get_trip_arc_departure(conflict.other_trip_id, index_arc_in_path_other_vehicle + 1) -
                complete_solution.get_trip_arc_departure(conflict.current_trip_id, index_arc_in_path_current_vehicle) -
                CONSTR_TOLERANCE;
    }

    auto check_if_possible_to_solve_conflict(const double &distance_to_cover,
                                             const double &slack_vehicle_one,
                                             const double &staggering_applied_vehicle_two) {
        if (slack_vehicle_one + staggering_applied_vehicle_two > distance_to_cover) {
            return true;
        }

        return false;
    }

    auto check_if_solution_is_admissible(Solution &complete_solution,
                                         Scheduler &scheduler) -> bool {
        if (!complete_solution.get_feasible_and_improving_flag()) {
            return false;
        }
        if (complete_solution.get_ties_flag()) {
            scheduler.increase_counter(SOLUTION_WITH_TIES);
            return false;
        }
        return true;
    }

    auto solve_conflict(Conflict &conflict, Solution &new_solution,
                        const Instance &instance, Scheduler &scheduler) {
        scheduler.increase_counter(EXPLORED_SOLUTIONS);
        bool conflict_is_not_solved = conflict.distance_to_cover > CONSTR_TOLERANCE;
        while (conflict_is_not_solved) {
            bool time_limit_reached = check_if_time_limit_is_reached(scheduler.get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) {
                break;
            }
            auto slack_is_enough = check_if_possible_to_solve_conflict(conflict.distance_to_cover,
                                                                       scheduler.get_trip_remaining_time_slack(
                                                                               new_solution, conflict.current_trip_id),
                                                                       scheduler.get_trip_staggering_applied(
                                                                               new_solution, conflict.other_trip_id));
            scheduler.set_slack_is_enough_flag(slack_is_enough);

            if (!scheduler.get_slack_is_enough_flag()) {
                scheduler.increase_counter(SLACK_NOT_ENOUGH); // Printing purposes
                break;
            }
            scheduler.apply_staggering_to_solve_conflict(new_solution, conflict);
            scheduler.update_existing_congested_schedule(new_solution, conflict);
            if (!new_solution.get_feasible_and_improving_flag()) { break; }
            update_distance_to_cover(new_solution, conflict, instance);
            conflict_is_not_solved = conflict.distance_to_cover > CONSTR_TOLERANCE;
        }
    }

    auto improve_solution(const Instance &instance,
                          const std::vector<Conflict> &conflicts_list,
                          Scheduler &scheduler,
                          Solution &current_solution) -> bool {
        Solution new_solution(current_solution);
        for (auto conflict: conflicts_list) {
            if (std::abs(conflict.distance_to_cover) < TOLERANCE) {
                continue;
            }
            solve_conflict(conflict, new_solution, instance, scheduler);
            bool time_limit_reached = check_if_time_limit_is_reached(scheduler.get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) {
                return false;
            }
            bool is_admissible = check_if_solution_is_admissible(new_solution, scheduler);
            if (is_admissible && scheduler.get_slack_is_enough_flag()) {
                if (scheduler.get_iteration() % 20 == 0) {
                    scheduler.construct_schedule(new_solution);
                }
                print_move(current_solution, new_solution, conflict);
                update_current_solution(current_solution, new_solution, conflict);
                _assert_solution_is_correct(new_solution, scheduler);
                return true;
            } else {
                reset_new_solution(current_solution, new_solution, conflict);
                continue;
            }
        }
        return false;
    }

    auto improve_towards_solution_quality(const Instance &instance,
                                          Solution &current_solution,
                                          Scheduler &scheduler) -> void {
        // Improve value of solution
        ConflictSearcherNew conflict_searcher(instance);
        bool is_improved = true;
        while (is_improved) { // Initially set to true
            bool time_limit_reached = check_if_time_limit_is_reached(scheduler.get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) { break; }
            scheduler.set_best_total_delay(current_solution.get_total_delay());
            auto conflicts_list = conflict_searcher.get_conflict_list(current_solution.get_schedule());
            sort_conflicts(conflicts_list);
            if (conflicts_list.empty()) { break; }
            is_improved = improve_solution(instance, conflicts_list, scheduler, current_solution);
        }
        scheduler.construct_schedule(current_solution);
    }

}
