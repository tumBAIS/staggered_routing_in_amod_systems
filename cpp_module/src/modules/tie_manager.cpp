#include <iostream>
#include <cmath>
#include "scheduler.h"

namespace cpp_module {


// Check if a vehicle has enough slack to solve a tie
    auto Scheduler::enough_slack_to_solve_tie(TripID trip_id, const Solution &solution) -> bool {
        auto trip_start_time = solution.get_trip_start_time(trip_id);
        auto slack_trip = get_trip_remaining_time_slack(trip_id, trip_start_time);
        return slack_trip > CONSTR_TOLERANCE;
    }


// Print a message when a tie is solved
    auto TieManager::print_tie_solved(const Tie &tie) -> void {
        std::cout << "Tie solved: Trip " << tie.vehicle_one
                  << " - Trip " << tie.vehicle_two
                  << " - Arc " << tie.arc << '\n';
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

                // Resolve ties as long as conditions hold
                while (check_tie(working_solution, tie) && working_solution.is_feasible()) {
                    working_solution.set_ties_flag(true);

                    if (enough_slack_to_solve_tie(vehicle_one, working_solution)) {
                        Solution new_solution = solve_tie(working_solution, tie);

                        // Validate the new solution
                        if (!new_solution.is_feasible()) {
                            break;  // Restore the previous solution
                        }

                        // Indicate the tie has been resolved
                        print_tie_solved(tie);
                        working_solution = new_solution;
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
                return true;
            }
        }
        complete_solution.set_ties_flag(false);
        return false;
    }

// Solve all ties in the solution
    auto Scheduler::solve_solution_ties(Solution &complete_solution) -> void {
        while (complete_solution.has_ties() && complete_solution.is_feasible()) {
            complete_solution.set_ties_flag(false);
            for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
                if (instance.get_conflicting_set(arc_id).empty()) {
                    continue;
                }
                solve_arc_ties(arc_id, complete_solution);
            }
        }
    }

    // Resolve a tie by staggering a vehicle
    auto Scheduler::solve_tie(Solution &initial_solution, const Tie &tie) -> Solution {

        // Stagger the trip slightly to resolve the tie

        auto start_times = initial_solution.copy_start_times();
        increase_trip_start_time(start_times, tie.vehicle_one, CONSTR_TOLERANCE + TOLERANCE);


        // Reconstruct the schedule with the updated solution
        //TODO: use update solution here
        return construct_solution(start_times);
    }


} // namespace cpp_module
