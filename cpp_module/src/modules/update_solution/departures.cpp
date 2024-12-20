// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::get_departure(double arg_time, TripID trip_id, Position arg_position, DepartureType arg_type,
                                  int arg_reinsertion_number) -> Departure {
        Departure departure{
                .time = arg_time,
                .arc_id=instance.get_arc_at_position_in_trip_route(trip_id, arg_position),
                .trip_id= trip_id,
                .position = arg_position,
                .event_type=arg_type,
                .reinsertion_number=arg_reinsertion_number
        };
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

    auto Scheduler::check_if_travel_departure_should_be_skipped(const Departure &departure) -> bool {
        bool is_valid_travel =
                (departure.position == get_trip_last_processed_position(departure.trip_id) + 1) &&
                (departure.reinsertion_number == get_trip_reinsertions(departure.trip_id));

        if (is_valid_travel) {
            return false;
        } else {
            return true;
        }
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
