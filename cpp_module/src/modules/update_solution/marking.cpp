//
// Created by anton on 11/12/2024.
//
#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::reinsert_other_in_queue(Solution &solution,
                                            const long otherVehicle,
                                            const long otherPosition,
                                            const double otherDeparture,
                                            const long arc) -> void {
        print_reinsertion_vehicle(arc, otherVehicle, otherDeparture);
        reset_other_schedule_to_reinsertion_time(solution, otherVehicle, otherPosition);
        last_processed_position[otherVehicle] = otherPosition - 1;
        other_trip_departure.trip_id = otherVehicle;
        other_trip_departure.arc_id = arc;
        other_trip_departure.time = otherDeparture;
        other_trip_departure.position = otherPosition;
        other_trip_departure.eventType = Departure::TRAVEL;
        number_of_reinsertions[otherVehicle]++;
        other_trip_departure.reinsertionNumber = number_of_reinsertions[otherVehicle];
        pq_departures.push(other_trip_departure);
    }

    auto Scheduler::decide_on_vehicles_maybe_to_mark(const VehicleSchedule &congestedSchedule,
                                                     const double currentNewArrival) -> void {
        for (long other_trip_id: vehicles_to_mark) {
            auto shouldMark = check_if_should_mark_given_current_arrival_time(
                    other_trip_id, currentNewArrival);  // O(1)
            if (shouldMark) {
                const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const double otherDeparture = congestedSchedule[other_trip_id][otherPosition];
                mark_vehicle(other_trip_id, otherDeparture, otherPosition);
                assert_no_vehicles_departing_before_are_marked(other_trip_id, congestedSchedule);
            }
        }
    }

    auto check_type_of_mark(const bool otherAlwaysFirst,
                            const bool switchOtherWithCurrentOrder,
                            const bool switchCurrentWithOtherOrder,
                            const bool currentAlwaysFirst,
                            const bool currentConflictsWithOther,
                            const bool otherOverlappedWithCurrent) -> Scheduler::VehicleShouldBeMarked {
        if (otherAlwaysFirst) {
            return Scheduler::NO;
        } else if (switchOtherWithCurrentOrder) {
            if (!otherOverlappedWithCurrent && !currentConflictsWithOther) {
                return Scheduler::NO;
            } else {
                return Scheduler::YES;
            }
        } else if (switchCurrentWithOtherOrder || currentAlwaysFirst) {
            return Scheduler::MAYBE;
        } else {
            throw std::invalid_argument("Check if other should be marked: undefined case");
        }
    }

    auto Scheduler::check_if_other_should_be_marked(const long otherVehicle,
                                                    const long otherPosition,
                                                    const bool currentConflictsWithOther) -> VehicleShouldBeMarked {
        assert_other_is_not_active(otherVehicle);
        // read info of other vehicle in original schedule (makes sense: it's not marked)
        auto otherOriginalDeparture = original_schedule[otherVehicle][otherPosition];
        auto currentOriginalDeparture = original_schedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = original_schedule[departure.trip_id][departure.position + 1];
        auto otherWasOriginallyFirst = check_if_other_is_first_in_original_schedule(otherVehicle,
                                                                                    otherOriginalDeparture,
                                                                                    currentOriginalDeparture);
        auto otherOverlappedWithCurrent = check_if_other_overlapped_with_current(otherVehicle, otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 currentOriginalArrival);
        bool otherIsFirstNow = check_if_other_is_first_in_current_schedule(otherVehicle, otherOriginalDeparture);
        bool currentWasOriginallyFirst = !otherWasOriginallyFirst;
        bool currentIsFirstNow = !otherIsFirstNow;
        // so far we can be sure to not mark the other conflict only if before and after the change was coming before
        bool otherAlwaysFirst = otherWasOriginallyFirst && otherIsFirstNow;
        bool switchOtherWithCurrentOrder = currentWasOriginallyFirst && otherIsFirstNow;
        bool switchCurrentWithOtherOrder = otherWasOriginallyFirst && currentIsFirstNow;
        bool currentAlwaysFirst = currentWasOriginallyFirst && currentIsFirstNow;
        return check_type_of_mark(otherAlwaysFirst, switchOtherWithCurrentOrder,
                                  switchCurrentWithOtherOrder, currentAlwaysFirst,
                                  currentConflictsWithOther, otherOverlappedWithCurrent);
    }

    auto Scheduler::check_if_should_mark_given_current_arrival_time(const TripID other_trip_id,
                                                                    const double currentVehicleNewArrival) -> bool {
        assert_other_is_not_active(other_trip_id);
        auto otherPosition = get_index(instance.get_trip_route(other_trip_id),
                                       departure.arc_id);
        auto otherOriginalDeparture = original_schedule[other_trip_id][otherPosition];
        auto otherOriginalArrival = original_schedule[other_trip_id][otherPosition + 1];
        auto currentOriginalDeparture = original_schedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = original_schedule[departure.trip_id][departure.position + 1];

        auto currentOverlappedWithOther = check_if_current_overlapped_with_other(other_trip_id,
                                                                                 otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 otherOriginalArrival);
        auto otherOverlappedWithCurrent = check_if_other_overlapped_with_current(other_trip_id, otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 currentOriginalArrival);

        auto otherOverlapsNowWithCurrent = check_if_other_overlaps_now_with_current(other_trip_id,
                                                                                    otherOriginalDeparture,
                                                                                    currentVehicleNewArrival);

        bool otherIsOriginallyFirst = check_if_other_is_first_in_original_schedule(other_trip_id,
                                                                                   otherOriginalDeparture,
                                                                                   currentOriginalDeparture);

        bool otherIsFirstNow = check_if_other_is_first_in_current_schedule(other_trip_id, otherOriginalDeparture);

        bool currentDidNotOverlapWithOther = !currentOverlappedWithOther;
        bool otherDoesNotOverlapWithCurrent = !otherOverlapsNowWithCurrent;
        bool currentIsOriginallyFirst = !otherIsOriginallyFirst;
        bool currentStartsFirstNow = !otherIsFirstNow;

        bool switchCurrentWithOtherOrder = otherIsOriginallyFirst && currentStartsFirstNow;
        bool vehiclesNeverOverlapped = currentDidNotOverlapWithOther && otherDoesNotOverlapWithCurrent;
        bool currentAlwaysFirst = currentIsOriginallyFirst && currentStartsFirstNow;
        bool otherAlwaysOverlaps = otherOverlappedWithCurrent && otherOverlapsNowWithCurrent;
        return check_conditions_to_mark(switchCurrentWithOtherOrder, vehiclesNeverOverlapped,
                                        currentAlwaysFirst, otherAlwaysOverlaps);
    }

    auto
    Scheduler::mark_vehicle(const long otherVehicle,
                            const double otherDeparture,
                            const long otherPosition) -> void {
        assert_other_is_not_active(otherVehicle);
        other_trip_departure.trip_id = otherVehicle;
        other_trip_departure.arc_id = departure.arc_id;
        other_trip_departure.time = otherDeparture;
        other_trip_departure.position = otherPosition;
        other_trip_departure.reinsertionNumber = 0;
        other_trip_departure.eventType = Departure::ACTIVATION;
        trip_status_list[otherVehicle] = STAGING;
        pq_departures.push(other_trip_departure);
    }
}