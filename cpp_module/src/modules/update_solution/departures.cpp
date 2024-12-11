//
// Created by anton on 11/12/2024.
//
#include <queue>
#include "scheduler.h"
#include "stdexcept"

auto
cpp_module::Scheduler::add_departure_to_priority_queue(const double releaseTimeVehicle, const TripID vehicle) -> void {
    departure.trip_id = vehicle;
    departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, 0);
    departure.position = 0;
    last_processed_position[departure.trip_id] = -1;
    departure.time = releaseTimeVehicle;
    departure.eventType = Departure::TRAVEL;
    departure.reinsertionNumber = 0;
    trip_status_list[departure.trip_id] = ACTIVE;
    pq_departures.push(departure);


}

auto cpp_module::Scheduler::check_if_activation_departure_should_be_skipped() -> bool {
    if (trip_status_list[departure.trip_id] == ACTIVE) {
        // trying to activate a vehicle which is active/reinserted -> this event should be skipped
        return true;
    } else if (trip_status_list[departure.trip_id] == STAGING) {
        // this event activates a staging vehicle and becomes a TRAVEL event
        return false;
    } else {
        throw std::invalid_argument("#SKIPDEPARTURE: undefined case");
    }
}

auto cpp_module::Scheduler::check_if_travel_departure_should_be_skipped() -> bool {

    if (departure.position == last_processed_position[departure.trip_id] + 1 &&
        departure.reinsertionNumber == number_of_reinsertions[departure.trip_id]) {
        return false;
    } else {
        printTravelDepartureToSkip();
        return true;
    }
}

auto cpp_module::Scheduler::check_if_departure_should_be_skipped() -> bool {
    if (departure.arc_id == 0) {
        return true; //vehicle at destination
    }
    if (departure.eventType == Departure::ACTIVATION) {
        return check_if_activation_departure_should_be_skipped();
    } else if (departure.eventType == Departure::TRAVEL) {
        return check_if_travel_departure_should_be_skipped();
    } else {
        throw std::invalid_argument("departureTime type not existent");
    }
}

auto cpp_module::Scheduler::activate_staging_vehicle() -> void {
    if (departure.eventType == Departure::ACTIVATION) {
        if (trip_status_list[departure.trip_id] == STAGING) {
            departure.eventType = Departure::TRAVEL;
            trip_status_list[departure.trip_id] = ACTIVE;
            last_processed_position[departure.trip_id] = departure.position - 1;
        } else if (trip_status_list[departure.trip_id] == INACTIVE) {
            throw std::invalid_argument("#UPDATEDEPARTURE: activating an INACTIVE vehicle");
        }
    }
}
