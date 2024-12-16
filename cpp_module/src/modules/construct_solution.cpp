#include "scheduler.h"
#include <queue>
#include <algorithm>
#include <iostream>

namespace cpp_module {

// Initialize conflicting sets for constructing the schedule
    auto initialize_conflicting_sets_for_construct_schedule(Instance &instance) -> void {
        long trip_id = 0;
        for (const auto &path: instance.get_trip_routes()) {
            for (auto arc_id: path) {
                instance.insert_trip_in_conflicting_set(arc_id, trip_id);
            }
            trip_id++;
        }
    }

// Find the index of an element in a vector
    auto get_index(const std::vector<long> &vec, long value) -> long {
        auto it = std::find(vec.begin(), vec.end(), value);
        return (it != vec.end()) ? static_cast<long>(it - vec.begin()) : -1;
    }

// Initialize the solution object
    auto initialize_complete_solution(Solution &complete_solution) -> void {
        complete_solution.set_total_delay(0);
        complete_solution.set_feasible_and_improving_flag(true);
        complete_solution.set_ties_flag(false);
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
    auto Scheduler::check_if_solution_is_admissible(double total_delay, const Departure &departure) const -> bool {
        if (departure.time > instance.get_trip_deadline(departure.trip_id) + TOLERANCE) {
            std::cout << "Deadline for vehicle " << departure.trip_id << " exceeded: "
                      << "Deadline: " << instance.get_trip_deadline(departure.trip_id)
                      << ", Position: " << departure.position
                      << ", Path length: " << instance.get_trip_route(departure.trip_id).size()
                      << ", Current time: " << departure.time << "\n";
            return false;
        }
        if (total_delay >= get_best_total_delay()) {
            return false;
        }
        return true;
    }

// Get the next departure from the priority queue
    auto Scheduler::get_next_departure(Solution &complete_solution) -> Departure {
        auto departure = get_and_pop_departure_from_pq();
        complete_solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        return departure;
    }

// Construct the schedule
    auto Scheduler::construct_schedule(Solution &complete_solution) -> void {
        // Initialize scheduler and complete solution
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

                bool schedule_is_feasible_and_improving =
                        check_if_solution_is_admissible(complete_solution.get_total_delay(), departure);

                if (!schedule_is_feasible_and_improving) {
                    complete_solution.set_feasible_and_improving_flag(false);
                }
            }
        }
    }

} // namespace cpp_module
