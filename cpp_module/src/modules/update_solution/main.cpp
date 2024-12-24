// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::update_total_delay_solution(Solution &current_solution, Solution &new_solution) -> void {
        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            // Skip trips that are not active
            if (get_trip_status(trip_id) != ACTIVE) {
                continue;
            }

            // Calculate old and new delays for the trip
            const double old_delay = current_solution.get_trip_arrival(trip_id) -
                                     current_solution.get_trip_start_time(trip_id) -
                                     instance.get_trip_free_flow_time(trip_id);

            const double new_delay = new_solution.get_trip_arrival(trip_id) -
                                     new_solution.get_trip_start_time(trip_id) -
                                     instance.get_trip_free_flow_time(trip_id);

            // Update the total delay in the new solution
            new_solution.increase_total_delay(new_delay - old_delay);
        }
    }


    auto Scheduler::update_existing_congested_schedule(Solution &initial_solution,
                                                       TripID trip_id,
                                                       TripID other_trip_id,
                                                       double distance_to_cover) -> Solution {
        initialize_scheduler_for_update_solution();


        Solution new_solution(initial_solution);

        apply_staggering_to_solve_conflict(new_solution, trip_id, other_trip_id, distance_to_cover);

        while (!is_pq_empty()) {

            auto departure = get_and_pop_departure_from_pq();

            const auto skip_departure = check_if_departure_should_be_skipped(departure);

            if (skip_departure) continue;

            activate_staging_vehicle(departure);

            new_solution.set_trip_arc_departure_time(departure.trip_id, departure.position, departure.time);

            clear_vehicles_to_mark();

            set_lazy_update_pq_flag(false);

            auto trip_arrival_time = process_vehicle(initial_solution, new_solution, departure);

            if (get_lazy_update_pq_flag()) {

                insert_departure_in_pq(departure);

                continue;
            }

            // Move the vehicle forward in the priority queue
            move_vehicle_forward(new_solution, trip_arrival_time, departure);
        }
        update_total_delay_solution(initial_solution, new_solution);
        return new_solution;
    }
}
