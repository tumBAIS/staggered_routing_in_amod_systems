#include <iostream>
#include <cmath>
#include "scheduler.h"
#include "random"

namespace cpp_module {


// Check if a vehicle has enough slack to solve a tie
    auto Scheduler::enough_slack_to_solve_tie(TripID trip_id, const Solution &solution, double num) -> bool {
        auto trip_start_time = solution.get_trip_start_time(trip_id);
        auto slack_trip = get_trip_remaining_time_slack(trip_id, trip_start_time);
        return slack_trip > num;
    }


    auto
    TieManager::print_tie_solved(const Tie &tie, const Solution &old_solution, const Solution &new_solution) -> void {
        const auto d1_old = old_solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one);
        const auto d2_old = old_solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two);
        const auto d1_new = new_solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one);
        const auto d2_new = new_solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two);

        const auto a1_old = old_solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one + 1);
        const auto a2_old = old_solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two + 1);
        const auto a1_new = new_solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one + 1);
        const auto a2_new = new_solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two + 1);

        std::cout << "Tie on Arc " << tie.arc << " solved: "
                  << "Trip " << tie.vehicle_one << " [D: " << d1_old << "→" << d1_new
                  << ", A: " << a1_old << "→" << a1_new << "], "
                  << "Trip " << tie.vehicle_two << " [D: " << d2_old << "→" << d2_new
                  << ", A: " << a2_old << "→" << a2_new << "]\n";
    }


    auto TieManager::check_tie(const Solution &solution, const Tie &tie) -> bool {
        auto dep_v1_pos1 = solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one);
        auto dep_v2_pos2 = solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two);
        auto dep_v1_pos1_next = solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one + 1);
        auto dep_v2_pos2_next = solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two + 1);

        return (std::abs(dep_v1_pos1 - dep_v2_pos2) < CONSTR_TOLERANCE - TOLERANCE) ||
               (std::abs(dep_v2_pos2 - dep_v1_pos1_next) < CONSTR_TOLERANCE - TOLERANCE) ||
               (std::abs(dep_v1_pos1 - dep_v2_pos2_next) < CONSTR_TOLERANCE - TOLERANCE);
    }


// Check if there are any ties on a given arc
    auto TieManager::check_arc_ties(ArcID arc_id, Solution &complete_solution) -> bool {
        for (auto vehicle_one: instance.get_conflicting_set(arc_id)) {
            long position_one = instance.get_arc_position_in_trip_route(arc_id, vehicle_one);

            for (auto vehicle_two: instance.get_conflicting_set(arc_id)) {
                if (vehicle_one < vehicle_two) {
                    long position_two = instance.get_arc_position_in_trip_route(arc_id, vehicle_two);
                    Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};
                    if (check_tie(complete_solution, tie)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    void Scheduler::solve_arc_ties(ArcID arc_id, Solution &working_solution) {
        const auto &conflicting_set = instance.get_conflicting_set(arc_id);

        for (const auto &vehicle_one: conflicting_set) {
            long position_one = instance.get_arc_position_in_trip_route(arc_id, vehicle_one);

            for (const auto &vehicle_two: conflicting_set) {
                if (vehicle_one == vehicle_two) continue;  // Skip identical vehicles

                long position_two = instance.get_arc_position_in_trip_route(arc_id, vehicle_two);
                Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};

                int attempts = 0;
                const int MAX_ATTEMPTS = 10;

                // Resolve ties as long as conditions hold
                while (check_tie(working_solution, tie) && attempts < MAX_ATTEMPTS) {
                    ++attempts;
                    working_solution.set_ties_flag(true);

                    if (enough_slack_to_solve_tie(vehicle_one, working_solution, 10 * CONSTR_TOLERANCE)) {
                        Solution new_solution = update_existing_congested_schedule(
                                working_solution,
                                tie.vehicle_one,
                                tie.vehicle_two,
                                10 * CONSTR_TOLERANCE
                        );

                        // Check if departure was not changed
                        if (std::abs(new_solution.get_trip_start_time(tie.vehicle_one) -
                                     working_solution.get_trip_start_time(tie.vehicle_one)
                        ) < TOLERANCE) {
                            // Force staggering
                            auto new_start_times = new_solution.get_start_times();
                            new_start_times[tie.vehicle_one] += 10 * CONSTR_TOLERANCE;
                            new_solution = construct_solution(new_start_times);
                        }


                        // Validate the new solution
                        if (!new_solution.is_feasible()) {
                            break;  // Restore the previous solution
                        }

                        // Indicate the tie has been resolved
                        print_tie_solved(tie, working_solution, new_solution);
                        working_solution = new_solution;
                        set_tie_solved_flag(true);
                    } else {
                        break;
                    }
                }
            }
        }
    }


// Check if the solution has any ties
    auto TieManager::check_if_solution_has_ties(Solution &complete_solution) -> bool {
        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
            if (instance.get_conflicting_set(arc_id).empty()) {
                continue;
            }

            if (check_arc_ties(arc_id, complete_solution)) {
                complete_solution.set_ties_flag(true);
                std::cout << "X Ties found in solution.\n";
                return true;
            }
        }
        complete_solution.set_ties_flag(false);
        std::cout << "✅ No ties in solution.\n";
        return false;
    }


// Solve all ties in the solution
    auto Scheduler::solve_solution_ties(Solution &complete_solution) -> void {
        int max_iterations = 10;
        int iteration_count = 0;

        while (complete_solution.has_ties()) {
            if (++iteration_count > max_iterations) {
                throw std::runtime_error("[ERROR] Maximum number of tie resolution iterations (10) exceeded.");
            }

            complete_solution.set_ties_flag(false);
            set_tie_solved_flag(false);

            for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
                if (instance.get_conflicting_set(arc_id).empty()) {
                    continue;
                }
                solve_arc_ties(arc_id, complete_solution);
            }

            if (!get_tie_solved_flag()) {
                break;
            }
        }
    }


} // namespace cpp_module
