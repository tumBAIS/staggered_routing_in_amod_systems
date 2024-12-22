#include "scheduler.h"
#include <queue>
#include <algorithm>
#include <iostream>

namespace cpp_module {


// Initialize the solution object
    auto initialize_complete_solution(Solution &complete_solution) -> void {
        complete_solution.set_total_delay(0);
        complete_solution.set_feasible_flag(true);
        complete_solution.set_ties_flag(false);
    }

    auto
    Scheduler::compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc, const double &departure_time) -> double {
        while (!arrivals_on_arc.empty() && arrivals_on_arc.top().time <= departure_time) {
            arrivals_on_arc.pop();
        }
        return static_cast<double>(arrivals_on_arc.size()) + 1.0;
    }

    auto Scheduler::compute_delay_on_arc(const double &vehicles_on_arc,
                                         const Instance &arg_instance,
                                         const long arc) -> double {
        if (arc == 0) {
            return 0.0;
        }

        // Pre-allocate vector for delays
        std::vector<double> delays_at_pieces;
        delays_at_pieces.reserve(arg_instance.get_number_of_pieces_delay_function() + 1);

        // Initialize delay calculation
        double height_prev_piece = 0.0;
        delays_at_pieces.push_back(0.0);

        // Loop through each piece of the delay function
        for (std::size_t i = 0; i < arg_instance.get_number_of_pieces_delay_function(); ++i) {
            double threshold_capacity = arg_instance.get_piece_threshold(i) * arg_instance.get_arc_capacity(arc);
            double slope = (arg_instance.get_arc_travel_time(arc) * arg_instance.get_piece_slope(i)) /
                           arg_instance.get_arc_capacity(arc);

            // Calculate delay for the current piece if vehicles exceed threshold capacity
            if (vehicles_on_arc > threshold_capacity) {
                double delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - threshold_capacity);
                delays_at_pieces.push_back(delay_current_piece);
            }

            // Update the height for the next piece
            if (i < arg_instance.get_number_of_pieces_delay_function() - 1) {
                double next_threshold_capacity =
                        arg_instance.get_piece_threshold(i + 1) * arg_instance.get_arc_capacity(arc);
                height_prev_piece += slope * (next_threshold_capacity - threshold_capacity);
            }
        }

        // Return the maximum delay calculated across all pieces
        return *std::max_element(delays_at_pieces.begin(), delays_at_pieces.end());
    }

// Initialize the scheduler
    auto Scheduler::initialize_scheduler(const std::vector<double> &release_times) -> void {
        // Reset priority queues and counters, and initialize priority queue for departures
        clear_departures_pq();
        clear_arrivals_on_arcs();
        Departure departure{};

        for (long trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            departure.time = release_times[trip_id];
            departure.trip_id = trip_id;
            departure.position = 0;
            departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
            insert_departure_in_pq(departure);
        }
    }

// Set the next departure of a vehicle and push it to the queue
    auto Scheduler::set_next_departure_and_push_to_queue(double delay, Departure &departure) -> void {
        departure.time += instance.get_arc_travel_time(departure.arc_id) + delay;
        insert_departure_in_arc_arrivals(departure.arc_id, departure);

        if (departure.position + 1 < instance.get_trip_route(departure.trip_id).size()) {
            departure.position++;
            departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
            insert_departure_in_pq(departure);
        }
    }

// Check if the current solution is admissible
    auto Scheduler::check_if_solution_is_feasible(const Departure &departure) const -> auto {
        if (departure.time > instance.get_trip_deadline(departure.trip_id) + TOLERANCE) {
            std::cout << "Deadline for vehicle " << departure.trip_id << " exceeded: "
                      << "Deadline: " << instance.get_trip_deadline(departure.trip_id)
                      << ", Position: " << departure.position
                      << ", Path length: " << instance.get_trip_route(departure.trip_id).size()
                      << ", Current time: " << departure.time << "\n";
            return false;
        }
        return true;
    }

// Get the next departure from the priority queue
    auto Scheduler::get_next_departure(Solution &complete_solution) -> Departure {
        auto departure = get_and_pop_departure_from_pq();
        complete_solution.set_trip_arc_departure_time(departure.trip_id, departure.position, departure.time);
        return departure;
    }

// Construct the schedule
    auto Scheduler::construct_solution(const std::vector<Time> &arg_start_times) -> Solution {
        // Initialize scheduler and complete solution
        Solution complete_solution(arg_start_times, instance);
        initialize_scheduler(complete_solution.get_start_times());
        initialize_complete_solution(complete_solution);

        while (!is_pq_empty()) {
            auto departure = get_next_departure(complete_solution);

            if (departure.position < instance.get_trip_route_size(departure.trip_id)) {
                const auto vehicles_on_arc = compute_vehicles_on_arc(get_arrivals_on_arc(departure.arc_id),
                                                                     departure.time);
                const auto delay = compute_delay_on_arc(vehicles_on_arc, instance, departure.arc_id);

                complete_solution.increase_total_delay(delay);

                set_next_departure_and_push_to_queue(delay, departure);

                if (!check_if_solution_is_feasible(departure)) {
                    complete_solution.set_feasible_flag(false);
                }
            }
        }
        check_if_solution_has_ties(complete_solution);
        if (complete_solution.has_ties()) {
            solve_solution_ties(complete_solution);
        }
        return complete_solution;

    }

} // namespace cpp_module
