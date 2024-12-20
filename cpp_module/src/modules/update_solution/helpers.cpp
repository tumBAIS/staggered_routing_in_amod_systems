// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::reset_other_schedule_to_reinsertion_time(Solution &initial_solution,
                                                             Solution &new_solution,
                                                             const long other_vehicle,
                                                             const long other_position) -> void {
        long steps_back = get_trip_last_processed_position(other_vehicle) - other_position;

        for (long step = 0; step < steps_back; ++step) {
            new_solution.set_trip_arc_departure_time(
                    other_vehicle,
                    other_position + step + 1,
                    initial_solution.get_trip_arc_departure(
                            other_vehicle,
                            other_position + step + 1
                    )
            );
        }
    }

    auto Scheduler::process_conflicting_set(Solution &initial_solution,
                                            Solution &new_solution,
                                            const Departure &departure) -> Time {
        // Update the number of vehicles on the arc for the conflicting set
        auto flow_on_arc = get_flow_on_arc(initial_solution, new_solution, departure);

        // Exit early if lazy update flag is set
        if (get_lazy_update_pq_flag()) {
            return UNUSED_VALUE;
        }

        // Check for ties in the conflicting set and update the flag
        if (check_arc_ties(departure.arc_id, new_solution)) {
            new_solution.set_ties_flag(true);
            return UNUSED_VALUE; // Exit early if a tie is found
        }

        // Compute the delay due to vehicles on the arc
        auto delay = compute_delay_on_arc(flow_on_arc, instance, departure.arc_id);

        // Calculate the updated arrival time for the current vehicle
        auto current_new_arrival = departure.time + delay + instance.get_arc_travel_time(departure.arc_id);

        // Check if the vehicle is late and update the flag
        if (check_if_vehicle_is_late(current_new_arrival, departure)) {
            new_solution.set_feasible_flag(false);
            return UNUSED_VALUE; // Exit early if the vehicle is late
        }

        // Decide on any vehicles that may need to be marked
        mark_waiting_trips(initial_solution, new_solution, current_new_arrival, departure);

        return current_new_arrival;
    }


    auto Scheduler::process_vehicle(Solution &initial_solution, Solution &new_solution, Departure &departure) -> Time {
        // Calculate new arrival time for the current vehicle

        if (!instance.is_conflicting_set_empty(departure.arc_id)) {
            auto trip_arrival_time = process_conflicting_set(initial_solution, new_solution, departure);
            return trip_arrival_time;
        }
        return departure.time + instance.get_arc_travel_time(departure.arc_id); // no congestion;
    }


    auto Scheduler::check_if_other_was_first(long other_vehicle,
                                             double other_original_departure,
                                             double current_original_departure,
                                             const Departure &departure) -> bool {
        bool other_is_first_in_original_schedule = (other_original_departure + TOLERANCE) <= current_original_departure;
        if (std::abs(other_original_departure - current_original_departure) <= TOLERANCE) {
            if (departure.trip_id < other_vehicle) {
                // Current vehicle would pass first - break tie
                other_is_first_in_original_schedule = false;
            }
        }
        return other_is_first_in_original_schedule;
    }

    auto Scheduler::check_if_other_is_first(long other_vehicle,
                                            double other_original_departure,
                                            const Departure &departure) -> bool {
        bool other_is_first_now = (other_original_departure + TOLERANCE) <= departure.time;
        if (std::abs(departure.time - other_original_departure) <= TOLERANCE) {
            if (departure.trip_id < other_vehicle) {
                // Current vehicle would pass first - break tie
                other_is_first_now = false;
            }
        }
        return other_is_first_now;
    }


    bool Scheduler::check_if_current_had_conflict_with_other(long other_vehicle,
                                                             double other_original_departure,
                                                             double current_original_departure,
                                                             double other_original_arrival,
                                                             const Departure &departure) {

        bool current_overlapped_with_other =
                (other_original_departure <= current_original_departure + TOLERANCE) &&
                (current_original_departure < other_original_arrival - TOLERANCE);

        if (std::abs(current_original_departure - other_original_departure) < TOLERANCE) {
            if (departure.trip_id < other_vehicle) {
                current_overlapped_with_other = false;
            }
        }

        return current_overlapped_with_other;
    }


    auto Scheduler::check_if_other_had_conflict_with_current(long other_vehicle,
                                                             double other_original_departure,
                                                             double current_original_departure,
                                                             double current_original_arrival,
                                                             const Departure &departure) -> bool {
        bool other_overlapped_with_current =
                (current_original_departure - TOLERANCE) <= other_original_departure &&
                other_original_departure < (current_original_arrival + TOLERANCE);
        if (std::abs(current_original_departure - other_original_departure) <= TOLERANCE) {
            if (other_vehicle < departure.trip_id) {
                other_overlapped_with_current = false;
            }
        }
        return other_overlapped_with_current;
    }

    auto Scheduler::check_if_other_has_conflict_with_current(long other_vehicle,
                                                             double other_original_departure,
                                                             double current_vehicle_new_arrival,
                                                             const Departure &departure) -> bool {
        bool other_overlaps_now_with_current =
                departure.time <= other_original_departure &&
                other_original_departure < current_vehicle_new_arrival;
        if (departure.time == other_original_departure) {
            if (other_vehicle < departure.trip_id) {
                other_overlaps_now_with_current = false;
            }
        }
        return other_overlaps_now_with_current;
    }


    auto Scheduler::move_vehicle_forward(Solution &new_solution,
                                         const double trip_arrival_time,
                                         Departure &departure) -> void {
        // Update the vehicle's schedule
        new_solution.set_trip_arc_departure_time(departure.trip_id, departure.position + 1,
                                                 trip_arrival_time);
        departure.time = trip_arrival_time;
        set_trip_last_processed_position(departure.trip_id, departure.position);
        departure.position++;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
        if (!is_arc_dummy(departure.arc_id)) {
            insert_departure_in_pq(departure);
        }
    }


    auto Scheduler::initialize_scheduler_for_update_solution() -> void {
        clear_departures_pq();
        set_lazy_update_pq_flag(false);
        initialize_status_vehicles();
    }

    auto Scheduler::initialize_priority_queue(const Conflict &conflict, Solution &solution) -> void {
        // Helper lambda to process and insert a departure into the priority queue
        auto process_and_insert_departure = [&](int trip_id) {
            auto departure = get_departure(
                    solution.get_trip_start_time(trip_id),
                    trip_id, 0, TRAVEL, 0
            );
            set_trip_last_processed_position(departure.trip_id, -1);
            set_trip_status(departure.trip_id, ACTIVE);
            insert_departure_in_pq(departure);
        };

        // Process staggering and destaggering vehicles
        if (conflict.staggering_current_vehicle != 0) {
            process_and_insert_departure(conflict.current_trip_id);
        }
        if (conflict.destaggering_other_vehicle != 0) {
            process_and_insert_departure(conflict.other_trip_id);
        }
    }

}
