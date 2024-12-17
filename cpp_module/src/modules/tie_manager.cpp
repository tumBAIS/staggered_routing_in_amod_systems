#include <iostream>
#include <cmath>
#include <queue>
#include "scheduler.h"

namespace cpp_module {


// Reset a solution to a previously correct state
    auto TieManager::reset_solution(Solution &complete_solution, long vehicle_one,
                                    const CorrectSolution &correct_solution) -> void {
        complete_solution.increase_trip_start_time(vehicle_one, -CONSTR_TOLERANCE);
        complete_solution.set_ties_flag(true);
        complete_solution.set_schedule(correct_solution.schedule);
        complete_solution.set_total_delay(correct_solution.total_delay);
        complete_solution.set_feasible_and_improving_flag(correct_solution.schedule_is_feasible_and_improving);
    }

// Check if a vehicle has enough slack to solve a tie
    auto Scheduler::enough_slack_to_solve_tie(TripID trip_id, const Solution &solution) -> bool {
        auto trip_start_time = solution.get_trip_start_time(trip_id);
        auto slack_trip = get_trip_remaining_time_slack(trip_id, trip_start_time);
        return slack_trip > CONSTR_TOLERANCE;
    }

// Create a snapshot of the current solution as the correct state
    auto TieManager::set_correct_solution(const Solution &complete_solution) -> CorrectSolution {
        return {complete_solution.get_schedule(), complete_solution.get_total_delay(), true};
    }

// Print a message when a tie is solved
    auto TieManager::print_tie_solved(const Tie &tie) -> void {
        std::cout << "Tie solved: Trip " << tie.vehicle_one
                  << " - Trip " << tie.vehicle_two
                  << " - Arc " << tie.arc << '\n';
    }

// Check if there is a tie between two vehicles
    auto TieManager::check_tie(const Solution &solution, const Tie &tie) -> bool {
        bool depart_at_same_time =
                std::abs(solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one)
                         - solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two)) <
                CONSTR_TOLERANCE - TOLERANCE;

        bool vehicle_one_arrives_at_departure =
                std::abs(solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two) -
                         solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one + 1)) <
                CONSTR_TOLERANCE - TOLERANCE;

        bool vehicle_two_arrives_at_departure =
                std::abs(solution.get_trip_arc_departure(tie.vehicle_one, tie.position_one)
                         - solution.get_trip_arc_departure(tie.vehicle_two, tie.position_two + 1)) <
                CONSTR_TOLERANCE - TOLERANCE;

        return depart_at_same_time || vehicle_one_arrives_at_departure || vehicle_two_arrives_at_departure;
    }


// Check if there are any ties on a given arc
    auto TieManager::check_arc_ties(ArcID arc_id, Solution &complete_solution) -> bool {
        for (auto vehicle_one: instance.get_conflicting_set(arc_id)) {
            long position_one = get_index(instance.get_trip_route(vehicle_one), arc_id);

            for (auto vehicle_two: instance.get_conflicting_set(arc_id)) {
                if (vehicle_one < vehicle_two) {
                    long position_two = get_index(instance.get_trip_route(vehicle_two), arc_id);
                    Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};
                    if (check_tie(complete_solution, tie)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

// Solve all ties on a specific arc
    auto Scheduler::solve_arc_ties(ArcID arc_id, Solution &complete_solution) -> void {
        const auto &conflicting_set = instance.get_conflicting_set(arc_id);

        for (auto vehicle_one: conflicting_set) {
            long position_one = get_index(instance.get_trip_route(vehicle_one), arc_id);

            for (auto vehicle_two: conflicting_set) {
                if (vehicle_one == vehicle_two) continue;  // Skip identical vehicles

                long position_two = get_index(instance.get_trip_route(vehicle_two), arc_id);

                Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};

                // Resolve ties as long as conditions hold
                while (check_tie(complete_solution, tie) &&
                       enough_slack_to_solve_tie(vehicle_one, complete_solution)) {
                    solve_tie(complete_solution, tie);
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
        complete_solution.set_ties_flag(false);

        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
            if (instance.get_conflicting_set(arc_id).empty()) {
                continue;
            }
            solve_arc_ties(arc_id, complete_solution);
        }
    }

    // Resolve a tie by staggering a vehicle
    void Scheduler::solve_tie(Solution &complete_solution, const Tie &tie) {

        // Save the current state in case we need to reset
        CorrectSolution correct_solution = set_correct_solution(complete_solution);

        // Stagger the trip slightly to resolve the tie
        complete_solution.increase_trip_start_time(tie.vehicle_one, CONSTR_TOLERANCE);

        // Reconstruct the schedule with the updated solution
        //TODO: use update solution here
        complete_solution = construct_solution(complete_solution.get_start_times());


        // Check if the new solution is valid
        if (!complete_solution.is_feasible_and_improving()) {
            // Restore the previous solution
            reset_solution(complete_solution, tie.vehicle_one, correct_solution);
            return;
        }

        // Print a message indicating the tie has been solved
        print_tie_solved(tie);
    }


} // namespace cpp_module
