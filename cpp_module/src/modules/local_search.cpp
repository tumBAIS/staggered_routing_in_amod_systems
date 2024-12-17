#include "local_search.h"
#include <iostream>
#include <iomanip>
#include <cmath>
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


    auto compare_conflicts(const Conflict &a, const Conflict &b) -> bool {
        if (a.delay_conflict > b.delay_conflict) {
            return true;
        } else if (a.delay_conflict == b.delay_conflict) {
            return a.current_trip_id > b.current_trip_id;
        }
        return false;
    }

    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void {
        if (!conflicts_in_schedule.empty()) {
            std::sort(conflicts_in_schedule.begin(),
                      conflicts_in_schedule.end(),
                      compare_conflicts);
        }
    }

    auto compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc, const double &departure_time) -> double {
        while (!arrivals_on_arc.empty() && arrivals_on_arc.top().time <= departure_time) {
            arrivals_on_arc.pop();
        }
        return static_cast<double>(arrivals_on_arc.size()) + 1.0;
    }

    auto compute_delay_on_arc(const double &vehicles_on_arc,
                              const Instance &arg_instance,
                              const long arc) -> double {
        if (arc == 0) {
            return 0.0;
        }

        std::vector<double> delays_at_pieces;
        delays_at_pieces.reserve(arg_instance.get_number_of_pieces_delay_function() + 1);

        double height_prev_piece = 0.0;
        delays_at_pieces.push_back(0.0);

        for (std::size_t i = 0; i < arg_instance.get_number_of_pieces_delay_function(); ++i) {
            const double threshold_capacity = arg_instance.get_piece_threshold(i) * arg_instance.get_arc_capacity(arc);
            const double slope = arg_instance.get_arc_travel_time(arc) * arg_instance.get_piece_slope(i) /
                                 arg_instance.get_arc_capacity(arc);

            if (vehicles_on_arc > threshold_capacity) {
                double delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - threshold_capacity);
                delays_at_pieces.push_back(delay_current_piece);
            }

            if (i < arg_instance.get_number_of_pieces_delay_function() - 1) {
                double next_threshold_capacity =
                        arg_instance.get_piece_threshold(i + 1) * arg_instance.get_arc_capacity(arc);
                height_prev_piece += slope * (next_threshold_capacity - threshold_capacity);
            }
        }

        return *std::max_element(delays_at_pieces.begin(), delays_at_pieces.end());
    }

    auto
    LocalSearch::create_conflict(long arc, double delay, ConflictingArrival &sorted_arrival) const -> Conflict {
        return Conflict{
                arc,
                current_vehicle_info.trip_id,
                sorted_arrival.vehicle,
                delay,
                sorted_arrival.arrival - current_vehicle_info.departure_time + CONSTR_TOLERANCE,
                0.0,
                0.0
        };
    }

    auto LocalSearch::get_instructions_conflict(const VehicleSchedule &congested_schedule,
                                                long other_position) -> InstructionsConflict {
        if (other_info.trip_id == current_vehicle_info.trip_id) {
            return InstructionsConflict::CONTINUE;
        }

        other_info.earliest_departure_time = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                           other_position);
        other_info.earliest_arrival_time = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                         other_position + 1);
        other_info.latest_departure_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                       other_position);
        other_info.latest_arrival_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                     other_position + 1);

        bool other_comes_before_and_cannot_overlap =
                other_info.latest_arrival_time <= current_vehicle_info.earliest_departure_time;
        bool other_comes_before_and_can_overlap =
                other_info.earliest_departure_time <= current_vehicle_info.earliest_departure_time &&
                current_vehicle_info.earliest_departure_time <= other_info.latest_arrival_time;
        bool other_comes_after_and_can_overlap =
                current_vehicle_info.earliest_departure_time <= other_info.earliest_departure_time &&
                other_info.earliest_departure_time <= current_vehicle_info.latest_departure_time;
        bool other_comes_after_and_cannot_overlap =
                other_info.earliest_departure_time >= current_vehicle_info.latest_departure_time;

        if (other_comes_before_and_cannot_overlap) {
            return InstructionsConflict::CONTINUE;
        } else if (other_comes_before_and_can_overlap || other_comes_after_and_can_overlap) {
            other_info.departure_time = congested_schedule[other_info.trip_id][other_position];
            other_info.arrival_time = congested_schedule[other_info.trip_id][other_position + 1];
            bool current_conflicts_with_other =
                    other_info.departure_time <= current_vehicle_info.departure_time &&
                    current_vehicle_info.departure_time < other_info.arrival_time;
            if (current_conflicts_with_other) {
                return InstructionsConflict::ADD_CONFLICT;
            }
            return InstructionsConflict::CONTINUE;
        } else if (other_comes_after_and_cannot_overlap) {
            return InstructionsConflict::BREAK;
        } else {
            throw std::invalid_argument("get_instructions_conflict: unspecified case!");
        }
    }

    auto LocalSearch::add_conflicts_to_conflict_list(std::vector<Conflict> &conflicts_list, long arc) -> void {
        std::sort(conflicting_arrivals.begin(), conflicting_arrivals.end(), compare_conflicting_arrivals);
        long vehicles_on_arc = 1;
        for (auto sorted_arrival: conflicting_arrivals) {
            vehicles_on_arc++;
            double conflict_delay = compute_delay_on_arc(vehicles_on_arc, instance, arc);
            Conflict conflict = create_conflict(arc, conflict_delay, sorted_arrival);
            conflicts_list.push_back(conflict);
        }
    }

    auto LocalSearch::update_current_vehicle_info(long current_vehicle,
                                                  const VehicleSchedule &congested_schedule,
                                                  long position) -> void {
        current_vehicle_info.trip_id = current_vehicle;
        current_vehicle_info.departure_time = congested_schedule[current_vehicle][position];
        current_vehicle_info.arrival_time = congested_schedule[current_vehicle][position + 1];
        current_vehicle_info.earliest_departure_time = instance.get_trip_arc_earliest_departure_time(current_vehicle,
                                                                                                     position);
        current_vehicle_info.latest_departure_time = instance.get_trip_arc_latest_departure_time(current_vehicle,
                                                                                                 position);
        current_vehicle_info.earliest_arrival_time = instance.get_trip_arc_earliest_departure_time(current_vehicle,
                                                                                                   position + 1);
        current_vehicle_info.latest_arrival_time = instance.get_trip_arc_latest_departure_time(current_vehicle,
                                                                                               position + 1);
    }

    auto LocalSearch::check_vehicle_has_delay(const VehicleSchedule &congested_schedule,
                                              long current_vehicle) -> bool {
        const double free_flow_travel_time_vehicle = instance.get_trip_free_flow_time(current_vehicle);
        const double congested_time_vehicle =
                congested_schedule[current_vehicle].back() - congested_schedule[current_vehicle].front();
        return congested_time_vehicle - free_flow_travel_time_vehicle > TOLERANCE;
    }

    auto LocalSearch::get_conflict_list(const VehicleSchedule &congested_schedule) -> std::vector<Conflict> {
        std::vector<Conflict> conflicts_list;
        for (auto current_vehicle = 0; current_vehicle < congested_schedule.size(); current_vehicle++) {
            bool vehicle_has_delay = check_vehicle_has_delay(congested_schedule, current_vehicle);
            if (vehicle_has_delay) {
                for (auto position = 0; position < congested_schedule[current_vehicle].size() - 1; position++) {
                    long arc = instance.get_arc_at_position_in_trip_route(current_vehicle, position);
                    double delay = congested_schedule[current_vehicle][position + 1] -
                                   congested_schedule[current_vehicle][position] -
                                   instance.get_arc_travel_time(arc);
                    if (delay > TOLERANCE) {
                        conflicting_arrivals.clear();
                        update_current_vehicle_info(current_vehicle, congested_schedule, position);
                        for (auto other_vehicle: instance.get_conflicting_set(arc)) {
                            other_info.trip_id = other_vehicle;
                            const long other_position = get_index(instance.get_trip_route(other_vehicle), arc);
                            auto instructions_conflict = get_instructions_conflict(congested_schedule, other_position);
                            if (instructions_conflict == InstructionsConflict::CONTINUE) {
                                continue;
                            } else if (instructions_conflict == InstructionsConflict::BREAK) {
                                break;
                            } else {
                                conflicting_arrival.arrival = other_info.arrival_time;
                                conflicting_arrival.vehicle = other_info.trip_id;
                                conflicting_arrivals.push_back(conflicting_arrival);
                            }
                        }
                        add_conflicts_to_conflict_list(conflicts_list, arc);
                    }
                }
            }
        }
        return conflicts_list;
    }

    // Generate an initial solution for local search
    auto LocalSearch::get_initial_solution(
            const std::vector<double> &arg_release_times,
            const std::vector<double> &arg_remaining_time_slack,
            const std::vector<double> &arg_staggering_applied
    ) -> Solution {

        Solution current_solution(arg_release_times, instance);
        scheduler.construct_schedule(current_solution);

        if (!current_solution.get_feasible_and_improving_flag()) {
            std::cout << "Initial solution is infeasible - local search stopped\n";
            return current_solution;
        }

        current_solution.set_remaining_time_slack(arg_remaining_time_slack);
        current_solution.set_staggering_applied(arg_staggering_applied);

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

    auto LocalSearch::run(std::vector<Time> &arg_start_times,
                          const std::vector<double> &arg_remaining_time_slack) -> Solution {
        // Improve value of solution

        auto staggering_applied = compute_staggering_applied(arg_start_times);
        auto arg_solution = get_initial_solution(arg_start_times, arg_remaining_time_slack, staggering_applied);


        std::cout << "Local search received a solution with " << std::round(arg_solution.get_total_delay())
                  << " sec of delay\n";

        if (!arg_solution.get_feasible_and_improving_flag()) {
            return arg_solution;
        }

        check_if_solution_has_ties(instance, arg_solution);

        if (arg_solution.get_ties_flag()) {
            solve_solution_ties(instance, arg_solution, scheduler);
        }

        bool is_improved = true;
        while (is_improved) { // Initially set to true
            bool time_limit_reached = check_if_time_limit_is_reached(get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) { break; }
            scheduler.set_best_total_delay(arg_solution.get_total_delay());
            auto conflicts_list = get_conflict_list(arg_solution.get_schedule());
            sort_conflicts(conflicts_list);
            if (conflicts_list.empty()) { break; }
            is_improved = improve_solution(conflicts_list, arg_solution);
        }
        scheduler.construct_schedule(arg_solution);
        return arg_solution;
    }


    auto Scheduler::stagger_trip(Solution &complete_solution, long vehicle, double staggering) -> void {
        complete_solution.increase_trip_start_time(vehicle, staggering);
        complete_solution.increase_staggering_applied(vehicle, staggering);
        complete_solution.increase_remaining_time_slack(vehicle, -staggering); // Staggering is negative
    }


    auto LocalSearch::reset_new_solution(const Solution &current_solution, Solution &new_solution,
                                         Conflict &conflict) -> void {
        scheduler.stagger_trip(new_solution,
                               conflict.current_trip_id,
                               -conflict.staggering_current_vehicle);
        conflict.staggering_current_vehicle = 0;
        scheduler.stagger_trip(new_solution,
                               conflict.other_trip_id,
                               conflict.destaggering_other_vehicle);
        conflict.destaggering_other_vehicle = 0;
        new_solution.set_schedule(current_solution.get_schedule());
        new_solution.set_total_delay(current_solution.get_total_delay());
        new_solution.set_ties_flag(current_solution.get_ties_flag());
        new_solution.set_feasible_and_improving_flag(current_solution.get_feasible_and_improving_flag());
    }

    auto LocalSearch::apply_staggering_to_solve_conflict(Solution &complete_solution,
                                                         Conflict &conflict) -> void {
        assert(conflict.distance_to_cover > 0);
        bool move_vehicle_one =
                conflict.distance_to_cover < complete_solution.get_trip_remaining_time_slack(conflict.current_trip_id);
        bool move_both_vehicles =
                conflict.distance_to_cover < complete_solution.get_trip_remaining_time_slack(conflict.current_trip_id) +
                                             complete_solution.get_trip_staggering_applied(conflict.other_trip_id);
        if (move_vehicle_one) {
            scheduler.stagger_trip(complete_solution, conflict.current_trip_id, conflict.distance_to_cover);
            conflict.staggering_current_vehicle += conflict.distance_to_cover;
            assert(conflict.distance_to_cover > 0);
        } else if (move_both_vehicles) {
            // Distance can be covered removing staggering to other vehicle
            auto staggering = std::max(0.0, complete_solution.get_trip_remaining_time_slack(conflict.current_trip_id));
            auto destaggering = conflict.distance_to_cover - staggering;
            scheduler.stagger_trip(complete_solution, conflict.current_trip_id, staggering);
            scheduler.stagger_trip(complete_solution, conflict.other_trip_id, -destaggering);
            conflict.staggering_current_vehicle += staggering;
            conflict.destaggering_other_vehicle += destaggering;
            assert(staggering > 0 || destaggering > 0);
        } else {
            throw std::invalid_argument("Applying staggering to solve conflict - undefined case");
        }
    }

    auto LocalSearch::update_current_solution(Solution &current_solution,
                                              const Solution &new_solution,
                                              Conflict &conflict) -> void {
        // Update current vehicle
        scheduler.stagger_trip(current_solution, conflict.current_trip_id, conflict.staggering_current_vehicle);
        scheduler.stagger_trip(current_solution, conflict.other_trip_id, -conflict.destaggering_other_vehicle);
        current_solution.set_schedule(new_solution.get_schedule());
        current_solution.set_total_delay(new_solution.get_total_delay());
        current_solution.set_ties_flag(new_solution.get_ties_flag());
        current_solution.set_feasible_and_improving_flag(new_solution.get_feasible_and_improving_flag());
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
        if (slack_vehicle_one + staggering_applied_vehicle_two > distance_to_cover) {
            return true;
        }

        return false;
    }

    auto LocalSearch::check_if_solution_is_admissible(Solution &complete_solution) -> bool {
        if (!complete_solution.get_feasible_and_improving_flag()) {
            return false;
        }
        if (complete_solution.get_ties_flag()) {
            scheduler.increase_counter(SOLUTION_WITH_TIES);
            return false;
        }
        return true;
    }

    auto LocalSearch::solve_conflict(Conflict &conflict, Solution &new_solution) {
        scheduler.increase_counter(EXPLORED_SOLUTIONS);
        bool conflict_is_not_solved = conflict.distance_to_cover > CONSTR_TOLERANCE;
        while (conflict_is_not_solved) {
            bool time_limit_reached = check_if_time_limit_is_reached(get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) {
                break;
            }
            auto slack_is_enough = check_if_possible_to_solve_conflict(conflict.distance_to_cover,
                                                                       new_solution.get_trip_remaining_time_slack(
                                                                               conflict.current_trip_id),
                                                                       new_solution.get_trip_staggering_applied(
                                                                               conflict.other_trip_id));
            scheduler.set_slack_is_enough_flag(slack_is_enough);

            if (!scheduler.get_slack_is_enough_flag()) {
                scheduler.increase_counter(SLACK_NOT_ENOUGH); // Printing purposes
                break;
            }
            apply_staggering_to_solve_conflict(new_solution, conflict);
            scheduler.update_existing_congested_schedule(new_solution, conflict);
            if (!new_solution.get_feasible_and_improving_flag()) { break; }
            update_distance_to_cover(new_solution, conflict);
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
            bool time_limit_reached = check_if_time_limit_is_reached(get_start_search_clock(),
                                                                     instance.get_max_time_optimization());
            if (time_limit_reached) {
                return false;
            }
            bool is_admissible = check_if_solution_is_admissible(new_solution);
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
}