// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::add_departure_to_priority_queue(const double release_time_vehicle, const TripID vehicle) -> void {
        departure.trip_id = vehicle;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, 0);
        departure.position = 0;
        set_trip_last_processed_position(departure.trip_id, -1);
        departure.time = release_time_vehicle;
        departure.event_type = Departure::TRAVEL;
        departure.reinsertion_number = 0;
        set_trip_status(departure.trip_id, ACTIVE);
        insert_departure_in_pq(departure);
    }

    auto Scheduler::check_if_activation_departure_should_be_skipped() -> bool {
        if (get_trip_status(departure.trip_id) == ACTIVE) {
            // Trying to activate a vehicle which is active/reinserted -> this event should be skipped
            return true;
        } else if (get_trip_status(departure.trip_id) == STAGING) {
            // This event activates a staging vehicle and becomes a TRAVEL event
            return false;
        } else {
            throw std::invalid_argument("#SKIPDEPARTURE: undefined case");
        }
    }

    auto Scheduler::check_if_travel_departure_should_be_skipped() -> bool {
        if (departure.position == get_trip_last_processed_position(departure.trip_id) + 1 &&
            departure.reinsertion_number == get_trip_reinsertions(departure.trip_id)) {
            return false;
        } else {
            print_travel_departure_to_skip();
            return true;
        }
    }

    auto Scheduler::check_if_departure_should_be_skipped() -> bool {
        if (departure.arc_id == 0) {
            return true; // Vehicle at destination
        }
        if (departure.event_type == Departure::ACTIVATION) {
            return check_if_activation_departure_should_be_skipped();
        } else if (departure.event_type == Departure::TRAVEL) {
            return check_if_travel_departure_should_be_skipped();
        } else {
            throw std::invalid_argument("departure_time type not existent");
        }
    }

    auto Scheduler::activate_staging_vehicle() -> void {
        if (departure.event_type == Departure::ACTIVATION) {
            if (get_trip_status(departure.trip_id) == STAGING) {
                departure.event_type = Departure::TRAVEL;
                set_trip_status(departure.trip_id, ACTIVE);
                set_trip_last_processed_position(departure.trip_id, departure.position - 1);
            } else if (get_trip_status(departure.trip_id) == INACTIVE) {
                throw std::invalid_argument("#UPDATEDEPARTURE: activating an INACTIVE vehicle");
            }
        }
    }
}
