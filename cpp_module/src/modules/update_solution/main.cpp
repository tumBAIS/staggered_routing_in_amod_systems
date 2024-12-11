// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::update_total_value_solution(Solution &complete_solution) -> void {

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (get_trip_status(trip_id) != ACTIVE) { continue; }

            const double old_delay_vehicle = get_last_original_trip_departure(trip_id) -
                                             get_original_trip_departure_at_position(trip_id, 0) -
                                             instance.get_trip_free_flow_time(trip_id);
            const double new_delay_vehicle = complete_solution.get_trip_schedule(trip_id).back() -
                                             complete_solution.get_trip_start_time(trip_id) -
                                             instance.get_trip_free_flow_time(trip_id);
            complete_solution.increase_total_delay(new_delay_vehicle - old_delay_vehicle);
        }
    }

    auto Scheduler::update_vehicle_schedule(Solution &solution,
                                            const double current_new_arrival,
                                            const Departure &departure) const -> void {
        // Update departure time and arrival in new schedule
        solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        solution.set_trip_arc_departure(departure.trip_id, departure.position + 1, current_new_arrival);
    }

    auto Scheduler::update_existing_congested_schedule(Solution &complete_solution,
                                                       const Conflict &conflict) -> void {

        initialize_scheduler_for_update_solution(complete_solution.get_schedule());
        initialize_status_vehicles();
        initialize_priority_queue(conflict, complete_solution);
        while (!is_pq_empty()) {
            auto departure = get_and_pop_departure_from_pq();
            const auto skip_departure = check_if_departure_should_be_skipped(departure);
            if (skip_departure) { continue; }
            print_departure();
            activate_staging_vehicle(departure);
            complete_solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
            clear_vehicles_to_mark();
            set_lazy_update_pq_flag(false);
            process_vehicle(complete_solution, departure);
            if (get_tie_found_flag() || get_trip_is_late_flag()) {
                complete_solution.set_feasible_and_improving_flag(false);
                return;
            }
            if (get_lazy_update_pq_flag()) {
                insert_departure_in_pq(departure);
                continue;
            }
        }
        update_total_value_solution(complete_solution);
        if (complete_solution.get_total_delay() >= get_best_total_delay()) {
            increase_counter(WORSE_SOLUTIONS);
            complete_solution.set_feasible_and_improving_flag(false);
        }
        assert_no_vehicles_are_late(complete_solution);
    }
}
