// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::get_departure(double arg_time, TripID trip_id, Position arg_position, DepartureType arg_type,
                                  TimeStamp arg_timestamp) -> Departure {
        Departure departure{
                .time = arg_time,
                .arc_id=instance.get_arc_at_position_in_trip_route(trip_id, arg_position),
                .trip_id= trip_id,
                .position = arg_position,
                .event_type=arg_type,
                .timestamp=arg_timestamp
        };

        set_trip_timestamp(trip_id, arg_timestamp);
        return departure;
    }

    auto Scheduler::check_if_activation_departure_should_be_skipped(const Departure &departure) -> bool {
        auto trip_status = get_trip_status(departure.trip_id);

        if (trip_status == ACTIVE) {
            // Skip activation for an already active or reinserted vehicle
            return true;
        } else if (trip_status == STAGING) {
            // Activation is valid for staging vehicles
            return false;
        } else {
            throw std::invalid_argument("#SKIPDEPARTURE: undefined case for trip status");
        }
    }

    auto Scheduler::check_if_travel_departure_should_be_skipped(const Departure &departure) const -> bool {
        // Retrieve the reinsertions count for the vehicle corresponding to the current departure

        // Retrieve the last processed position for the vehicle corresponding to the current departure
        Position last_processed_position_vehicle = get_trip_last_processed_position(departure.trip_id);

        // Check if the departure's position is exactly one step ahead of the last processed position
        bool is_sequential_position = (departure.position == last_processed_position_vehicle + 1);

        // Check if the departure's reinsertion count matches the stored reinsertion count for the vehicle
        bool is_matching_timestamp = (departure.timestamp == get_trip_timestamp(departure.trip_id));

        // If both conditions are not met, this departure should be skipped
        bool should_skip_departure = !(is_sequential_position && is_matching_timestamp);


        return should_skip_departure;
    }


    auto Scheduler::check_if_departure_should_be_skipped(const Departure &departure) -> bool {
        if (is_arc_dummy(departure.arc_id)) {
            return true; // Skip if vehicle has reached its destination
        }

        switch (departure.event_type) {
            case ACTIVATION:
                return check_if_activation_departure_should_be_skipped(departure);
            case TRAVEL:
                return check_if_travel_departure_should_be_skipped(departure);
            default:
                throw std::invalid_argument("departure_time type not existent");
        }
    }


    auto Scheduler::activate_staging_vehicle(Departure &departure) -> void {
        if (departure.event_type != ACTIVATION) {
            return; // No activation needed for non-ACTIVATION events
        }

        auto trip_status = get_trip_status(departure.trip_id);

        if (trip_status == STAGING) {
            departure.event_type = TRAVEL;
            set_trip_status(departure.trip_id, ACTIVE);
            set_trip_last_processed_position(departure.trip_id, departure.position - 1);
        } else if (trip_status == INACTIVE) {
            throw std::invalid_argument(
                    "#UPDATEDEPARTURE: Attempted to activate an INACTIVE vehicle");
        }
    }

}
