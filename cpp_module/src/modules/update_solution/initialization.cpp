//
// Created by anton on 11/12/2024.
//
#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {


    auto Scheduler::initialize_status_vehicles() -> void {
        trip_status_list = std::vector<vehicleStatusType>(instance.get_number_of_trips(), INACTIVE);
        number_of_reinsertions = std::vector<long>(instance.get_number_of_trips(), 0);
        last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
    }

    auto
    Scheduler::initialize_scheduler_for_update_solution(const VehicleSchedule &congestedSchedule) -> void {
        original_schedule = congestedSchedule;
        pq_departures = MinQueueDepartures();
        departure = Departure();
        other_trip_departure = Departure();
//        greatestTimeAnalyzedOnArcs = std::vector<double>(instance.numberOfArcs, 0);
        tie_found = false;
        lazy_update_pq = false;
        trip_is_late = false;
        iteration++;
        print_iteration_number();
    }

    auto
    Scheduler::initialize_priority_queue(const Conflict &conflict, Solution &solution) -> void {
        // add vehicles which are staggered at this iteration of the algorithm.
        if (conflict.staggeringCurrentVehicle != 0) {
            add_departure_to_priority_queue(solution.get_trip_start_time(conflict.current_trip_id),
                                            conflict.current_trip_id);
            solution.set_trip_arc_departure(conflict.current_trip_id, 0,
                                            solution.get_trip_start_time(conflict.current_trip_id));
        }
        if (conflict.destaggeringOtherVehicle != 0) {
            add_departure_to_priority_queue(solution.get_trip_start_time(conflict.other_trip_id),
                                            conflict.other_trip_id);
            solution.set_trip_arc_departure(conflict.other_trip_id, 0,
                                            solution.get_trip_start_time(conflict.other_trip_id));
        }

    }

}
