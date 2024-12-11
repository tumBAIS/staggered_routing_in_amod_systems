// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::update_total_value_solution(Solution &complete_solution) -> void {

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (trip_status_list[trip_id] != ACTIVE) { continue; }

            const double old_delay_vehicle = original_schedule[trip_id].back() -
                                             original_schedule[trip_id][0] -
                                             instance.get_trip_free_flow_time(trip_id);
            const double new_delay_vehicle = complete_solution.get_trip_schedule(trip_id).back() -
                                             complete_solution.get_trip_start_time(trip_id) -
                                             instance.get_trip_free_flow_time(trip_id);
            complete_solution.increase_total_delay(new_delay_vehicle - old_delay_vehicle);
        }
    }

    auto Scheduler::update_vehicle_schedule(Solution &solution,
                                            const double current_new_arrival) const -> void {
        // Update departure time and arrival in new schedule
        solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        solution.set_trip_arc_departure(departure.trip_id, departure.position + 1, current_new_arrival);
    }

    auto Scheduler::update_existing_congested_schedule(Solution &complete_solution,
                                                       const Conflict &conflict) -> void {

        initialize_scheduler_for_update_solution(complete_solution.get_schedule());
        initialize_status_vehicles();
        initialize_priority_queue(conflict, complete_solution);
        while (!pq_departures.empty()) {
            departure = pq_departures.top();
            pq_departures.pop();
            const auto skip_departure = check_if_departure_should_be_skipped();
            if (skip_departure) { continue; }
            print_departure();
            activate_staging_vehicle();
            complete_solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
            vehicles_to_mark.clear();
            lazy_update_pq = false;
            process_vehicle(complete_solution);
            if (tie_found || trip_is_late) {
                complete_solution.set_feasible_and_improving_flag(false);
                return;
            }
            if (lazy_update_pq) {
                pq_departures.push(departure);
                continue;
            }
        }
        update_total_value_solution(complete_solution);
        if (complete_solution.get_total_delay() >= best_total_delay) {
            worse_solutions++;
            complete_solution.set_feasible_and_improving_flag(false);
        }
        assert_no_vehicles_are_late(complete_solution);
    }
}
