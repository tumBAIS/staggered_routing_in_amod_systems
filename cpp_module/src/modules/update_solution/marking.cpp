// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::reinsert_other_in_queue(Solution &solution,
                                            const long other_vehicle,
                                            const long other_position,
                                            const double other_departure,
                                            const long arc) -> void {
        print_reinsertion_vehicle(arc, other_vehicle, other_departure);
        reset_other_schedule_to_reinsertion_time(solution, other_vehicle, other_position);
        last_processed_position[other_vehicle] = other_position - 1;
        other_trip_departure.trip_id = other_vehicle;
        other_trip_departure.arc_id = arc;
        other_trip_departure.time = other_departure;
        other_trip_departure.position = other_position;
        other_trip_departure.event_type = Departure::TRAVEL;
        number_of_reinsertions[other_vehicle]++;
        other_trip_departure.reinsertion_number = number_of_reinsertions[other_vehicle];
        pq_departures.push(other_trip_departure);
    }

    auto Scheduler::decide_on_vehicles_maybe_to_mark(const VehicleSchedule &congested_schedule,
                                                     const double current_new_arrival) -> void {
        for (long other_trip_id: vehicles_to_mark) {
            auto should_mark = check_if_should_mark_given_current_arrival_time(
                    other_trip_id, current_new_arrival);  // O(1)
            if (should_mark) {
                const long other_position = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const double other_departure = congested_schedule[other_trip_id][other_position];
                mark_vehicle(other_trip_id, other_departure, other_position);
                assert_no_vehicles_departing_before_are_marked(other_trip_id, congested_schedule);
            }
        }
    }

    auto check_type_of_mark(const bool other_always_first,
                            const bool switch_other_with_current_order,
                            const bool switch_current_with_other_order,
                            const bool current_always_first,
                            const bool current_conflicts_with_other,
                            const bool other_overlapped_with_current) -> Scheduler::VehicleShouldBeMarked {
        if (other_always_first) {
            return Scheduler::NO;
        } else if (switch_other_with_current_order) {
            if (!other_overlapped_with_current && !current_conflicts_with_other) {
                return Scheduler::NO;
            } else {
                return Scheduler::YES;
            }
        } else if (switch_current_with_other_order || current_always_first) {
            return Scheduler::MAYBE;
        } else {
            throw std::invalid_argument("Check if other should be marked: undefined case");
        }
    }

    auto Scheduler::check_if_other_should_be_marked(const long other_vehicle,
                                                    const long other_position,
                                                    const bool current_conflicts_with_other) -> VehicleShouldBeMarked {
        assert_other_is_not_active(other_vehicle);
        // Read info of other vehicle in original schedule (makes sense: it's not marked)
        auto other_original_departure = original_schedule[other_vehicle][other_position];
        auto current_original_departure = original_schedule[departure.trip_id][departure.position];
        auto current_original_arrival = original_schedule[departure.trip_id][departure.position + 1];
        auto other_was_originally_first = check_if_other_is_first_in_original_schedule(other_vehicle,
                                                                                       other_original_departure,
                                                                                       current_original_departure);
        auto other_overlapped_with_current = check_if_other_overlapped_with_current(other_vehicle,
                                                                                    other_original_departure,
                                                                                    current_original_departure,
                                                                                    current_original_arrival);
        bool other_is_first_now = check_if_other_is_first_in_current_schedule(other_vehicle, other_original_departure);
        bool current_was_originally_first = !other_was_originally_first;
        bool current_is_first_now = !other_is_first_now;
        // So far we can be sure to not mark the other conflict only if before and after the change was coming before
        bool other_always_first = other_was_originally_first && other_is_first_now;
        bool switch_other_with_current_order = current_was_originally_first && other_is_first_now;
        bool switch_current_with_other_order = other_was_originally_first && current_is_first_now;
        bool current_always_first = current_was_originally_first && current_is_first_now;
        return check_type_of_mark(other_always_first, switch_other_with_current_order,
                                  switch_current_with_other_order, current_always_first,
                                  current_conflicts_with_other, other_overlapped_with_current);
    }

    auto Scheduler::check_if_should_mark_given_current_arrival_time(const TripID other_trip_id,
                                                                    const double current_vehicle_new_arrival) -> bool {
        assert_other_is_not_active(other_trip_id);
        auto other_position = get_index(instance.get_trip_route(other_trip_id),
                                        departure.arc_id);
        auto other_original_departure = original_schedule[other_trip_id][other_position];
        auto other_original_arrival = original_schedule[other_trip_id][other_position + 1];
        auto current_original_departure = original_schedule[departure.trip_id][departure.position];
        auto current_original_arrival = original_schedule[departure.trip_id][departure.position + 1];

        auto current_overlapped_with_other = check_if_current_overlapped_with_other(other_trip_id,
                                                                                    other_original_departure,
                                                                                    current_original_departure,
                                                                                    other_original_arrival);
        auto other_overlapped_with_current = check_if_other_overlapped_with_current(other_trip_id,
                                                                                    other_original_departure,
                                                                                    current_original_departure,
                                                                                    current_original_arrival);

        auto other_overlaps_now_with_current = check_if_other_overlaps_now_with_current(other_trip_id,
                                                                                        other_original_departure,
                                                                                        current_vehicle_new_arrival);

        bool other_is_originally_first = check_if_other_is_first_in_original_schedule(other_trip_id,
                                                                                      other_original_departure,
                                                                                      current_original_departure);

        bool other_is_first_now = check_if_other_is_first_in_current_schedule(other_trip_id, other_original_departure);

        bool current_did_not_overlap_with_other = !current_overlapped_with_other;
        bool other_does_not_overlap_with_current = !other_overlaps_now_with_current;
        bool current_is_originally_first = !other_is_originally_first;
        bool current_starts_first_now = !other_is_first_now;

        bool switch_current_with_other_order = other_is_originally_first && current_starts_first_now;
        bool vehicles_never_overlapped = current_did_not_overlap_with_other && other_does_not_overlap_with_current;
        bool current_always_first = current_is_originally_first && current_starts_first_now;
        bool other_always_overlaps = other_overlapped_with_current && other_overlaps_now_with_current;
        return check_conditions_to_mark(switch_current_with_other_order, vehicles_never_overlapped,
                                        current_always_first, other_always_overlaps);
    }

    auto Scheduler::mark_vehicle(const long other_vehicle,
                                 const double other_departure,
                                 const long other_position) -> void {
        assert_other_is_not_active(other_vehicle);
        other_trip_departure.trip_id = other_vehicle;
        other_trip_departure.arc_id = departure.arc_id;
        other_trip_departure.time = other_departure;
        other_trip_departure.position = other_position;
        other_trip_departure.reinsertion_number = 0;
        other_trip_departure.event_type = Departure::ACTIVATION;
        trip_status_list[other_vehicle] = STAGING;
        pq_departures.push(other_trip_departure);
    }
}
