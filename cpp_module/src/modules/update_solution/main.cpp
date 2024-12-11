//
// Created by anton on 11/12/2024.
//
#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::update_total_value_solution(Solution &completeSolution) -> void {

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (trip_status_list[trip_id] != ACTIVE) { continue; }

            const double oldDelayVehicle = original_schedule[trip_id].back() -
                                           original_schedule[trip_id][0] -
                                           instance.get_trip_free_flow_time(trip_id);
            const double newDelayVehicle = completeSolution.get_trip_schedule(trip_id).back() -
                                           completeSolution.get_trip_start_time(trip_id) -
                                           instance.get_trip_free_flow_time(trip_id);
            completeSolution.increase_total_delay(newDelayVehicle - oldDelayVehicle);
        }
    }

    auto Scheduler::update_vehicle_schedule(Solution &solution,
                                            const double currentNewArrival) const -> void {
        // update departureTime and arrival in new schedule
        solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        solution.set_trip_arc_departure(departure.trip_id, departure.position + 1, currentNewArrival);
    }

    auto Scheduler::update_existing_congested_schedule(Solution &completeSolution,
                                                       const Conflict &conflict) -> void {

        initialize_scheduler_for_update_solution(completeSolution.get_schedule());
        initialize_status_vehicles();
        initialize_priority_queue(conflict, completeSolution);
        while (!pq_departures.empty()) {
            departure = pq_departures.top();
            pq_departures.pop();
            const auto skipDeparture = check_if_departure_should_be_skipped();
            if (skipDeparture) { continue; }
            _printDeparture();
            activate_staging_vehicle();
            completeSolution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
            vehicles_to_mark.clear();
            lazy_update_pq = false;
            process_vehicle(completeSolution);
            if (tie_found || trip_is_late) {
                completeSolution.set_feasible_and_improving_flag(false);
                return;
            }
            if (lazy_update_pq) {
                pq_departures.push(departure);
                continue;
            }
        }
        update_total_value_solution(completeSolution);
        if (completeSolution.get_total_delay() >= best_total_delay) {
            worseSolutions++;
            completeSolution.set_feasible_and_improving_flag(false);
        }
        _assertNoVehiclesAreLate(completeSolution);
    }
}