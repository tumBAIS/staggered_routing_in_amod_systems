#include "local_search.h"
#include <iostream>
#include <iomanip>
#include <cmath>
#include <queue>
#include <cassert>
#include <chrono>

namespace cpp_module {


    auto LocalSearch::check_if_time_limit_is_reached() -> bool {
        auto time_now = clock() / (double) CLOCKS_PER_SEC;
        auto duration = (time_now - start_search_clock);
        if (duration > instance.get_max_time_optimization()) {
            std::cout << "STOPPING LOCAL SEARCH - MAX TIME LIMIT REACHED \n";
            return true;
        }
        return false;
    }


    auto compare_conflicts(const Conflict &a, const Conflict &b) -> bool {
        // Compare delays with tolerance
        if (std::abs(a.delay_conflict - b.delay_conflict) > TOLERANCE) {
            return a.delay_conflict > b.delay_conflict; // Higher delay comes first
        }

        // If delays are equal within tolerance, compare trip IDs
        return a.current_trip_id > b.current_trip_id; // Larger trip ID comes first
    }


    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void {
        if (!conflicts_in_schedule.empty()) {
            std::sort(conflicts_in_schedule.begin(),
                      conflicts_in_schedule.end(),
                      compare_conflicts);
        }
    }


    auto LocalSearch::create_conflict(long arc, double delay, const TripInfo &trip_info,
                                      const TripInfo &conflicting_trip_info) -> Conflict {
        return Conflict{
                .arc = arc,
                .current_trip_id = trip_info.trip_id,
                .other_trip_id = conflicting_trip_info.trip_id,
                .delay_conflict = delay,
                .distance_to_cover = (conflicting_trip_info.arrival_time - trip_info.departure_time) + CONSTR_TOLERANCE,
                .staggering_current_vehicle = 0.0,
                .destaggering_other_vehicle = 0.0
        };
    }

    auto LocalSearch::get_instructions_conflict(const TripInfo &trip_info,
                                                const TripInfo &other_info) -> InstructionsConflict {
        // Check conditions for overlap and non-overlap
        bool other_before_no_overlap = other_info.latest_arrival_time <= trip_info.earliest_departure_time;
        bool other_before_with_overlap = other_info.earliest_departure_time <= trip_info.earliest_departure_time &&
                                         trip_info.earliest_departure_time <= other_info.latest_arrival_time;
        bool other_after_with_overlap = trip_info.earliest_departure_time <= other_info.earliest_departure_time &&
                                        other_info.earliest_departure_time <= trip_info.latest_departure_time;
        bool other_after_no_overlap = other_info.earliest_departure_time >= trip_info.latest_departure_time;

        // Decision-making logic
        if (other_before_no_overlap) {
            return InstructionsConflict::CONTINUE;
        }

        if (other_before_with_overlap || other_after_with_overlap) {
            bool current_conflicts_with_other = other_info.departure_time <= trip_info.departure_time &&
                                                trip_info.departure_time < other_info.arrival_time;
            return current_conflicts_with_other ? InstructionsConflict::ADD_CONFLICT
                                                : InstructionsConflict::CONTINUE;
        }

        if (other_after_no_overlap) {
            return InstructionsConflict::BREAK;
        }

        // Fallback for unspecified cases
        throw std::invalid_argument("get_instructions_conflict: unspecified case!");
    }


    auto LocalSearch::get_trip_info_struct(long current_trip,
                                           const Solution &solution,
                                           long position) -> TripInfo {
        TripInfo trip_info{
                .trip_id=current_trip,
                .departure_time=solution.get_trip_arc_departure(current_trip, position),
                .arrival_time= solution.get_trip_arc_departure(current_trip, position + 1),
                .earliest_departure_time= instance.get_trip_arc_earliest_departure_time(current_trip, position),
                .latest_departure_time=instance.get_trip_arc_latest_departure_time(current_trip, position),
                .latest_arrival_time=instance.get_trip_arc_latest_departure_time(current_trip, position + 1)
        };
        return trip_info;
    }

    auto LocalSearch::check_vehicle_has_delay(const Solution &solution,
                                              long trip_id) -> bool {
        const double fft_trip = instance.get_trip_free_flow_time(trip_id);
        const double travel_time_trip = solution.get_trip_arrival(trip_id) - solution.get_trip_start_time(trip_id);
        return travel_time_trip - fft_trip > TOLERANCE;
    }

    auto LocalSearch::find_conflicts_on_arc(long arc,
                                            double arc_delay,
                                            const Solution &solution,
                                            const TripInfo &trip_info,
                                            const std::vector<long> &conflicting_set)
    -> std::vector<Conflict> {
        std::vector<Conflict> conflicts_list;
        std::vector<TripInfo> conflicting_trips_info_list;

        // Analyze conflicts for the current arc
        for (auto other_trip: conflicting_set) {
            if (other_trip == trip_info.trip_id) {
                continue; // Skip the same trip
            }

            const long other_position = get_index(instance.get_trip_route(other_trip), arc);
            auto conflicting_trip_info = get_trip_info_struct(other_trip, solution, other_position);
            auto instructions_conflict = get_instructions_conflict(trip_info, conflicting_trip_info);

            if (instructions_conflict == InstructionsConflict::CONTINUE) {
                continue;
            } else if (instructions_conflict == InstructionsConflict::BREAK) {
                break;
            }

            conflicting_trips_info_list.push_back(conflicting_trip_info);
        }

        // Create conflicts based on the collected conflicting trips
        for (const auto &conflicting_trip_info: conflicting_trips_info_list) {
            conflicts_list.push_back(create_conflict(arc, arc_delay, trip_info, conflicting_trip_info));
        }

        return conflicts_list;
    }

    auto LocalSearch::get_conflicts_list(const Solution &solution) -> std::vector<Conflict> {
        std::vector<Conflict> conflicts_list;

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (!check_vehicle_has_delay(solution, trip_id)) {
                continue; // Skip vehicles without delay
            }

            for (auto position = 0; position < instance.get_trip_route_size(trip_id) - 1; ++position) {
                long arc = instance.get_arc_at_position_in_trip_route(trip_id, position);

                double arc_delay = solution.get_trip_arc_departure(trip_id, position + 1) -
                                   solution.get_trip_arc_departure(trip_id, position) -
                                   instance.get_arc_travel_time(arc);

                if (arc_delay <= TOLERANCE) {
                    continue; // Skip if delay is within tolerance
                }

                // Gather trip information and find conflicts for the current arc
                auto trip_info = get_trip_info_struct(trip_id, solution, position);
                auto conflicting_set = instance.get_conflicting_set(arc);

                auto arc_conflicts = find_conflicts_on_arc(arc, arc_delay, solution, trip_info, conflicting_set);
                conflicts_list.insert(conflicts_list.end(), arc_conflicts.begin(), arc_conflicts.end());
            }
        }

        sort_conflicts(conflicts_list);
        return conflicts_list;
    }


    // Generate an initial solution for local search
    auto LocalSearch::get_initial_solution(const std::vector<double> &arg_release_times) -> Solution {

        auto current_solution = scheduler.construct_solution(arg_release_times);

        if (!current_solution.is_feasible()) {
            std::cout << "Initial solution is infeasible - local search stopped\n";
            return current_solution;
        }

        return current_solution;
    }

    auto LocalSearch::compute_staggering_applied(const std::vector<Time> &arg_start_times) {
        // Allocate space for the results
        std::vector<Time> staggering_applied(arg_start_times.size());

        for (TripID trip_id = 0; trip_id < arg_start_times.size(); trip_id++) {
            // Calculate the staggering for each trip
            staggering_applied[trip_id] = arg_start_times[trip_id] - instance.get_trip_release_time(trip_id);
        }

        // Return the results
        return staggering_applied;
    }

    auto LocalSearch::compute_remaining_time_slack(const std::vector<Time> &arg_start_times) {
        // Allocate space for the results
        std::vector<Time> time_slack_trips(arg_start_times.size());

        for (TripID trip_id = 0; trip_id < arg_start_times.size(); trip_id++) {
            // Calculate the staggering for each trip
            time_slack_trips[trip_id] =
                    instance.get_trip_arc_latest_departure_time(trip_id, 0) - arg_start_times[trip_id];
        }

        // Return the results
        return time_slack_trips;
    }

    auto LocalSearch::print_initial_delay(const Solution &arg_solution) -> void {
        std::cout << "Local search received a solution with " << std::round(arg_solution.get_total_delay())
                  << " sec of delay\n";
    }

    auto LocalSearch::print_infeasible_message() -> void {
        std::cout << "Solution is infeasible -- stopping local search.\n";
    }

    auto LocalSearch::run(std::vector<Time> &arg_start_times) -> Solution {
        // Get the initial solution and print its delay
        auto arg_solution = get_initial_solution(arg_start_times);
        print_initial_delay(arg_solution);

        // If the solution is not feasible, return immediately
        if (!arg_solution.is_feasible()) {
            print_infeasible_message();
            return arg_solution;
        }

        // Resolve ties if any exist in the solution
        if (check_if_solution_has_ties(arg_solution)) {
            scheduler.solve_solution_ties(arg_solution);
        }

        // Iteratively improve the solution
        bool is_improved = true;
        while (is_improved) {
            increase_counter(ITERATION);
            // Check for time limit
            if (check_if_time_limit_is_reached()) break;

            // Store delay of the best solution found
            set_best_total_delay(arg_solution.get_total_delay());

            // Identify and sort conflicts
            auto conflicts_list = get_conflicts_list(arg_solution);

            // Stop if no conflicts remain
            if (conflicts_list.empty()) {
                break;
            }

            // Attempt to improve the solution
            is_improved = improve_solution(conflicts_list, arg_solution);
        }

        // Construct the final solution and return it
        return scheduler.construct_solution(arg_solution.get_start_times());
    }


    auto LocalSearch::reset_new_solution(const Solution &current_solution, Solution &new_solution,
                                         Conflict &conflict) -> void {
        new_solution.increase_trip_start_time(conflict.current_trip_id, -conflict.staggering_current_vehicle);
        conflict.staggering_current_vehicle = 0;
        new_solution.increase_trip_start_time(conflict.other_trip_id, conflict.destaggering_other_vehicle);
        conflict.destaggering_other_vehicle = 0;
        new_solution.set_schedule(current_solution.get_schedule());
        new_solution.set_total_delay(current_solution.get_total_delay());
        new_solution.set_ties_flag(current_solution.get_ties_flag());
        new_solution.set_feasible_flag(current_solution.is_feasible());
    }

    void LocalSearch::apply_staggering_to_solve_conflict(Solution &complete_solution,
                                                         Conflict &conflict) {
        assert(conflict.distance_to_cover > 0);

        // Retrieve current and other vehicle start times
        auto current_start_time = complete_solution.get_trip_start_time(conflict.current_trip_id);
        auto other_start_time = complete_solution.get_trip_start_time(conflict.other_trip_id);

        // Calculate conditions for moving vehicles
        bool move_vehicle_one =
                conflict.distance_to_cover <
                scheduler.get_trip_remaining_time_slack(conflict.current_trip_id, current_start_time) + TOLERANCE;

        bool move_both_vehicles =
                conflict.distance_to_cover <
                scheduler.get_trip_remaining_time_slack(conflict.current_trip_id, current_start_time) +
                scheduler.get_trip_staggering_applied(conflict.other_trip_id, other_start_time) + TOLERANCE;

        if (move_vehicle_one) {
            // Move only the current vehicle
            complete_solution.increase_trip_start_time(conflict.current_trip_id, conflict.distance_to_cover);
            conflict.staggering_current_vehicle += conflict.distance_to_cover;
            assert(conflict.distance_to_cover > 0);

        } else if (move_both_vehicles) {
            // Distance can be covered by removing staggering from the other vehicle
            auto staggering = std::max(0.0, scheduler.get_trip_remaining_time_slack(conflict.current_trip_id,
                                                                                    current_start_time));
            auto destaggering = conflict.distance_to_cover - staggering;

            complete_solution.increase_trip_start_time(conflict.current_trip_id, staggering);
            complete_solution.increase_trip_start_time(conflict.other_trip_id, -destaggering);

            conflict.staggering_current_vehicle += staggering;
            conflict.destaggering_other_vehicle += destaggering;

            assert(staggering > 0 || destaggering > 0);

        } else {
            // Throw a descriptive error with current values
            std::ostringstream error_message;
            error_message << "Undefined case in applying staggering to solve conflict:\n"
                          << "Conflict Details:\n"
                          << "  Distance to Cover: " << conflict.distance_to_cover << "\n"
                          << "  Current Trip ID: " << conflict.current_trip_id << "\n"
                          << "  Other Trip ID: " << conflict.other_trip_id << "\n"
                          << "  Current Trip Slack: "
                          << scheduler.get_trip_remaining_time_slack(conflict.current_trip_id, current_start_time)
                          << "\n"
                          << "  Other Trip Staggering Applied: "
                          << scheduler.get_trip_staggering_applied(conflict.other_trip_id, other_start_time) << "\n"
                          << "  Tolerance: " << TOLERANCE << "\n"
                          << "  Slack is enough: " << scheduler.get_slack_is_enough_flag() << "\n";

            throw std::invalid_argument(error_message.str());
        }
    }

    auto LocalSearch::update_current_solution(Solution &current_solution,
                                              const Solution &new_solution,
                                              Conflict &conflict) -> void {
        // Update current vehicle
        current_solution.increase_trip_start_time(conflict.current_trip_id, conflict.staggering_current_vehicle);
        current_solution.increase_trip_start_time(conflict.other_trip_id, -conflict.destaggering_other_vehicle);
        current_solution.set_schedule(new_solution.get_schedule());
        current_solution.set_total_delay(new_solution.get_total_delay());
        current_solution.set_ties_flag(new_solution.get_ties_flag());
        current_solution.set_feasible_flag(new_solution.is_feasible());
    }

    auto LocalSearch::print_move(const Solution &old_solution,
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


    auto LocalSearch::update_distance_to_cover(const Solution &complete_solution,
                                               Conflict &conflict) -> void {
        auto index_arc_in_path_current_vehicle = get_index(instance.get_trip_route(conflict.current_trip_id),
                                                           conflict.arc);
        auto index_arc_in_path_other_vehicle = get_index(instance.get_trip_route(conflict.other_trip_id), conflict.arc);

        conflict.distance_to_cover =
                complete_solution.get_trip_arc_departure(conflict.other_trip_id, index_arc_in_path_other_vehicle + 1) -
                complete_solution.get_trip_arc_departure(conflict.current_trip_id, index_arc_in_path_current_vehicle) -
                CONSTR_TOLERANCE;
    }

    auto LocalSearch::check_if_possible_to_solve_conflict(const double &distance_to_cover,
                                                          const double &slack_vehicle_one,
                                                          const double &staggering_applied_vehicle_two) {
        if (slack_vehicle_one + staggering_applied_vehicle_two + TOLERANCE > distance_to_cover) {
            return true;
        }

        return false;
    }

    auto LocalSearch::check_if_solution_is_admissible(Solution &complete_solution) -> bool {
        if (!complete_solution.is_feasible()) {
            return false;
        }

        if (complete_solution.get_total_delay() > best_total_delay) {
            return false;
        }

        if (complete_solution.get_ties_flag()) {
            increase_counter(SOLUTION_WITH_TIES);
            return false;
        }
        return true;
    }

    auto LocalSearch::solve_conflict(Conflict &conflict, Solution &new_solution) {
        // Increment explored solutions counter
        increase_counter(EXPLORED_SOLUTIONS);

        // Initial state checks
        bool conflict_is_not_solved = conflict.distance_to_cover > CONSTR_TOLERANCE;


        while (conflict_is_not_solved) {
            // Check if the time limit for the search is reached
            auto current_trip_start_time = new_solution.get_trip_start_time(conflict.current_trip_id);
            auto other_trip_start_time = new_solution.get_trip_start_time(conflict.other_trip_id);
            if (check_if_time_limit_is_reached()) break;  // Exit the loop if time limit is reached


            // Check if there is enough slack to solve the conflict
            bool slack_is_enough = check_if_possible_to_solve_conflict(
                    conflict.distance_to_cover,
                    scheduler.get_trip_remaining_time_slack(conflict.current_trip_id, current_trip_start_time),
                    scheduler.get_trip_staggering_applied(conflict.other_trip_id, other_trip_start_time)
            );

            scheduler.set_slack_is_enough_flag(slack_is_enough);

            if (!scheduler.get_slack_is_enough_flag()) {
                increase_counter(SLACK_NOT_ENOUGH);  // For logging/debug purposes
                break;  // Exit if no slack is sufficient
            }

            // Apply staggering to solve the conflict
            apply_staggering_to_solve_conflict(new_solution, conflict);

            // Update the schedule with the new solution
            scheduler.update_existing_congested_schedule(new_solution, conflict);

            // Check if the solution is feasible and improving
            if (!new_solution.is_feasible()) {
                increase_counter(WORSE_SOLUTIONS);
                break;  // Exit if no feasible or improving solution is found
            }

            // Update the distance to cover after applying the changes
            update_distance_to_cover(new_solution, conflict);

            // Re-evaluate if the conflict is solved
            conflict_is_not_solved = conflict.distance_to_cover > CONSTR_TOLERANCE;
        }
    }


    auto LocalSearch::improve_solution(const std::vector<Conflict> &conflicts_list,
                                       Solution &current_solution) -> bool {
        Solution new_solution(current_solution);
        for (auto conflict: conflicts_list) {
            if (std::abs(conflict.distance_to_cover) < TOLERANCE) {
                continue;
            }
            solve_conflict(conflict, new_solution);
            if (check_if_time_limit_is_reached()) return false;
            bool is_admissible = check_if_solution_is_admissible(new_solution);
            if (is_admissible && scheduler.get_slack_is_enough_flag()) {
                if (get_iteration() % 20 == 0) {
                    new_solution = scheduler.construct_solution(new_solution.get_start_times());
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
}