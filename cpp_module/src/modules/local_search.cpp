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
        auto duration = (time_now - start_algo_global_clock);
        if (duration > instance.get_max_time_optimization()) {
            std::cout << "STOPPING LOCAL SEARCH - MAX TIME LIMIT REACHED \n";
            return true;
        }
        return false;
    }


    auto LocalSearch::create_conflict(long arc, double delay, const TripInfo &trip_info,
                                      const TripInfo &other_trip_info) -> Conflict {
        return Conflict{
                .arc = arc,
                .trip_id = trip_info.trip_id,
                .current_position = trip_info.position,
                .other_trip_id = other_trip_info.trip_id,
                .other_position = other_trip_info.position,
                .delay = delay,
                .distance_to_cover = (other_trip_info.arrival_time - trip_info.departure_time) + 2 * CONSTR_TOLERANCE,
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
                .position=position,
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

            const long other_position = instance.get_arc_position_in_trip_route(arc, other_trip);
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
            auto conflict = create_conflict(arc, arc_delay, trip_info, conflicting_trip_info);
            if (conflict.distance_to_cover > TOLERANCE) {
                conflicts_list.push_back(conflict);
            }
        }

        return conflicts_list;
    }

    auto LocalSearch::get_conflicts_queue(const Solution &solution) -> ConflictsQueue {
        ConflictsQueue conflicts_queue;
        size_t total_size = instance.get_number_of_trips() * instance.get_number_of_arcs();
        conflicts_queue.reserve(total_size); // Preallocate memory for the expected number of elements


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
                for (auto arc_conflict: arc_conflicts) {
                    conflicts_queue.push(arc_conflict);
                }
            }
        }

        return conflicts_queue;
    }


    auto LocalSearch::print_initial_delay(const Solution &arg_solution) -> void {
        std::cout << "Local search received a solution with " << std::round(arg_solution.get_total_delay())
                  << " sec of delay\n";
    }

    auto LocalSearch::print_infeasible_message() -> void {
        std::cout << "Solution is infeasible -- stopping local search.\n";
    }

    auto LocalSearch::print_search_statistics(double start_run_clock) -> void {
        auto time_now = get_current_time_in_seconds();
        auto elapsed_time = time_now - start_run_clock;

        // Print the elapsed time and search statistics in a neat format
        std::cout << "Search Statistics\n";
        std::cout << "-------------------\n";
        std::cout << "Elapsed Time (seconds)  : " << std::fixed << std::setprecision(2) << elapsed_time << "\n";
        std::cout << "Infeasible Solutions    : " << get_counter(CounterName::INFEASIBLE_SOLUTIONS) << "\n";
        std::cout << "Slack Not Enough        : " << get_counter(CounterName::SLACK_NOT_ENOUGH) << "\n";
        std::cout << "Solutions with Ties     : " << get_counter(CounterName::SOLUTION_WITH_TIES) << "\n";
        std::cout << "Worse Solutions         : " << get_counter(CounterName::WORSE_SOLUTIONS) << "\n";
        std::cout << "Iterations              : " << get_counter(CounterName::ITERATION) << "\n";
    }


    auto LocalSearch::run(std::vector<Time> &arg_start_times) -> Solution {
        // Get the initial solution and print its delay
        auto start_run_clock = get_current_time_in_seconds();
        reset_counters();
        auto best_found_solution = scheduler.construct_solution(arg_start_times);

        print_initial_delay(best_found_solution);

        // If the solution is not feasible, return immediately
        if (!best_found_solution.is_feasible()) {
            print_infeasible_message();
            return best_found_solution;
        }

        // Resolve ties if any exist in the solution
        if (check_if_solution_has_ties(best_found_solution)) {
            scheduler.solve_solution_ties(best_found_solution);
        }

        // Iteratively improve the solution
        set_improvement_is_found(true); // Local search field
        while (get_improvement_is_found()) {
            // Check for time limit
            if (check_if_time_limit_is_reached()) break;

            // Store delay of the best solution found
            set_improvement_is_found(false); // Local search field

            // Identify and sort conflicts
            auto conflicts_queue = get_conflicts_queue(best_found_solution);

            // Stop if no conflicts remain
            if (conflicts_queue.empty()) {
                break;
            }

            // Attempt to improve the solution
            best_found_solution = improve_solution(conflicts_queue, best_found_solution);
        }

        if (verbose) {
            print_search_statistics(start_run_clock);
        }

        // Construct the final solution and return it
        return scheduler.construct_solution(best_found_solution.get_start_times());
    }


    auto LocalSearch::print_move(const Solution &best_known_solution,
                                 const Solution &new_solution,
                                 const Conflict &conflict) -> void {
        if (verbose || get_counter(ITERATION) % 50 == 0) {

            std::ostringstream output;

            auto staggering_applied = new_solution.get_trip_start_time(conflict.trip_id) -
                                      best_known_solution.get_trip_start_time(conflict.trip_id);
            if (staggering_applied > TOLERANCE) {
                output << "Staggering trip " << conflict.trip_id
                       << " by " << std::fixed << std::setprecision(2)
                       << staggering_applied << "; ";
            }

            auto destaggering_applied = best_known_solution.get_trip_start_time(conflict.other_trip_id) -
                                        new_solution.get_trip_start_time(conflict.other_trip_id);

            if (destaggering_applied > TOLERANCE) {
                output << "destaggering trip " << conflict.other_trip_id
                       << " by " << std::fixed << std::setprecision(2)
                       << destaggering_applied << "; ";
            }

            output << "new total delay: " << std::fixed << std::setprecision(2)
                   << new_solution.get_total_delay()
                   << "; delay improvement: "
                   << best_known_solution.get_total_delay() - new_solution.get_total_delay();

            std::cout << output.str() << std::endl;
        }

    }

    auto LocalSearch::check_if_possible_to_solve_conflict(const Conflict &conflict,
                                                          const Solution &solution) -> bool {
        // Retrieve trip start times
        auto current_trip_start_time = solution.get_trip_start_time(conflict.trip_id);
        auto other_trip_start_time = solution.get_trip_start_time(conflict.other_trip_id);

        // Calculate slack and staggering
        auto slack_vehicle_one = scheduler.get_trip_remaining_time_slack(conflict.trip_id,
                                                                         current_trip_start_time);
        auto staggering_vehicle_two = scheduler.get_trip_staggering_applied(conflict.other_trip_id,
                                                                            other_trip_start_time);

        // Check if the conflict can be resolved
        return (slack_vehicle_one + staggering_vehicle_two + TOLERANCE > conflict.distance_to_cover);
    }


    auto LocalSearch::solve_conflict(Conflict &conflict, Solution &initial_solution) -> Solution {

        // Exit early if the conflict cannot be resolved
        if (!check_if_possible_to_solve_conflict(conflict, initial_solution)) {
            increase_counter(SLACK_NOT_ENOUGH);
            return initial_solution;
        }

        // Generate a new solution by updating the schedule
        auto new_solution = scheduler.update_existing_congested_schedule(initial_solution,
                                                                         conflict.trip_id,
                                                                         conflict.other_trip_id,
                                                                         conflict.distance_to_cover);

        // Return the new solution if it is feasible and improves the total delay
        if (new_solution.is_feasible()) {
            if (!new_solution.has_ties()) {
                if (new_solution.get_total_delay() < initial_solution.get_total_delay() - TOLERANCE) {
                    set_improvement_is_found(true);
                    return new_solution;
                } else {
                    increase_counter(WORSE_SOLUTIONS); // Count only worse solutions
                }
            } else {
                increase_counter(SOLUTION_WITH_TIES); // Count solutions with ties only
            }
        } else {
            increase_counter(INFEASIBLE_SOLUTIONS); // Count infeasible solutions only
        }

        // Return the initial solution if no improvement was found
        return initial_solution;
    }


    auto LocalSearch::improve_solution(ConflictsQueue &conflicts_queue,
                                       Solution &best_known_solution) -> Solution {

        while (!conflicts_queue.empty()) {
            if (check_if_time_limit_is_reached()) break;
            auto conflict = conflicts_queue.top();
            conflicts_queue.pop();
            conflict.update(best_known_solution, instance);

            if (conflict.has_delay()) {
                //Check if it is still most urgent conflict
                if (!conflicts_queue.empty() && conflicts_queue.top().delay > conflict.delay + TOLERANCE) {
                    conflicts_queue.push(conflict);
                    continue;
                }
            } else {
                continue;
            }
            increase_counter(ITERATION);
            auto new_solution = solve_conflict(conflict, best_known_solution);
            if (new_solution.get_total_delay() < best_known_solution.get_total_delay() - TOLERANCE) {
                print_move(best_known_solution, new_solution, conflict);
                best_known_solution = new_solution;
                conflict.update(best_known_solution, instance);
                if (conflict.has_delay()) {
                    conflicts_queue.push(conflict);
                }
            }
        }

        return best_known_solution;
    }
}