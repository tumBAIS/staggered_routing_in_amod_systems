#include <iostream>
#include <cmath>
#include "scheduler.h"
#include <queue>

namespace cpp_module {

// Structure to store the correct solution state
    struct CorrectSolution {
        VehicleSchedule schedule;
        double total_delay;
        bool schedule_is_feasible_and_improving;
    };

// Reset a solution to a previously correct state
    auto
    reset_solution(Solution &complete_solution, long vehicle_one, const CorrectSolution &correct_solution) -> void {
        stagger_trip(complete_solution, vehicle_one, -CONSTR_TOLERANCE);
        complete_solution.set_ties_flag(true);
        complete_solution.set_schedule(correct_solution.schedule);
        complete_solution.set_total_delay(correct_solution.total_delay);
        complete_solution.set_feasible_and_improving_flag(correct_solution.schedule_is_feasible_and_improving);
    }

// Check if a vehicle has enough slack to solve a tie
    auto check_slack_to_solve_tie(double slack_vehicle) -> bool {
        return slack_vehicle > CONSTR_TOLERANCE;
    }

// Create a snapshot of the current solution as the correct state
    auto set_correct_solution(const Solution &complete_solution) -> CorrectSolution {
        return {complete_solution.get_schedule(), complete_solution.get_total_delay(), true};
    }

// Print a message when a tie is solved
    auto print_tie_solved(const Tie &tie) -> void {
        std::cout << "Tie solved: Trip " << tie.vehicle_one
                  << " - Trip " << tie.vehicle_two
                  << " - Arc " << tie.arc << '\n';
    }

// Check if there is a tie between two vehicles
    auto check_if_vehicles_have_tie(const VehicleSchedule &congested_schedule, const Tie &tie) -> bool {
        bool depart_at_same_time = std::abs(
                congested_schedule[tie.vehicle_one][tie.position_one] -
                congested_schedule[tie.vehicle_two][tie.position_two]) < CONSTR_TOLERANCE - TOLERANCE;

        bool vehicle_one_arrives_at_departure = std::abs(
                congested_schedule[tie.vehicle_two][tie.position_two] -
                congested_schedule[tie.vehicle_one][tie.position_one + 1]) < CONSTR_TOLERANCE - TOLERANCE;

        bool vehicle_two_arrives_at_departure = std::abs(
                congested_schedule[tie.vehicle_one][tie.position_one] -
                congested_schedule[tie.vehicle_two][tie.position_two + 1]) < CONSTR_TOLERANCE - TOLERANCE;

        return depart_at_same_time || vehicle_one_arrives_at_departure || vehicle_two_arrives_at_departure;
    }

// Resolve a tie by staggering a vehicle
    auto solve_tie(Solution &complete_solution, const Tie &tie, Scheduler &scheduler) -> void {
        bool has_tie = check_if_vehicles_have_tie(complete_solution.get_schedule(), tie);
        bool slack_is_enough = check_slack_to_solve_tie(
                complete_solution.get_trip_remaining_time_slack(tie.vehicle_one));

        while (has_tie && slack_is_enough) {
            CorrectSolution correct_solution = set_correct_solution(complete_solution);
            stagger_trip(complete_solution, tie.vehicle_one, CONSTR_TOLERANCE);
            scheduler.construct_schedule(complete_solution);

            if (!complete_solution.get_feasible_and_improving_flag()) {
                reset_solution(complete_solution, tie.vehicle_one, correct_solution);
                return;
            }

            print_tie_solved(tie);
            has_tie = check_if_vehicles_have_tie(complete_solution.get_schedule(), tie);
            slack_is_enough = check_slack_to_solve_tie(
                    complete_solution.get_trip_remaining_time_slack(tie.vehicle_one));
        }
    }

// Check if there are any ties on a given arc
    auto check_arc_ties(const Instance &instance, ArcID arc_id, Solution &complete_solution) -> bool {
        for (auto vehicle_one: instance.get_conflicting_set(arc_id)) {
            long position_one = get_index(instance.get_trip_route(vehicle_one), arc_id);

            for (auto vehicle_two: instance.get_conflicting_set(arc_id)) {
                if (vehicle_one < vehicle_two) {
                    long position_two = get_index(instance.get_trip_route(vehicle_two), arc_id);
                    Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};
                    if (check_if_vehicles_have_tie(complete_solution.get_schedule(), tie)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

// Solve all ties on a specific arc
    auto
    solve_arc_ties(const Instance &instance, ArcID arc_id, Solution &complete_solution, Scheduler &scheduler) -> void {
        for (auto vehicle_one: instance.get_conflicting_set(arc_id)) {
            long position_one = get_index(instance.get_trip_route(vehicle_one), arc_id);

            for (auto vehicle_two: instance.get_conflicting_set(arc_id)) {
                if (vehicle_one != vehicle_two) {
                    long position_two = get_index(instance.get_trip_route(vehicle_two), arc_id);
                    Tie tie = {vehicle_one, vehicle_two, position_one, position_two, arc_id};
                    solve_tie(complete_solution, tie, scheduler);
                }
            }
        }
    }


// Check if the solution has any ties
    auto check_if_solution_has_ties(const Instance &instance, Solution &complete_solution) -> void {
        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
            if (instance.get_conflicting_set(arc_id).empty()) {
                continue;
            }

            if (check_arc_ties(instance, arc_id, complete_solution)) {
                complete_solution.set_ties_flag(true);
                return;
            }
        }
        complete_solution.set_ties_flag(false);
    }

// Solve all ties in the solution
    auto solve_solution_ties(const Instance &instance, Solution &complete_solution, Scheduler &scheduler) -> void {
        complete_solution.set_ties_flag(false);

        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); ++arc_id) {
            if (instance.get_conflicting_set(arc_id).empty()) {
                continue;
            }

            solve_arc_ties(instance, arc_id, complete_solution, scheduler);
        }
    }

} // namespace cpp_module
