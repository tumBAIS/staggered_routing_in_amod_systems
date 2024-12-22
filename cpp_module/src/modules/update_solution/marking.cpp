// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::reinsert_other_in_queue(Solution &initial_solution,
                                            Solution &new_solution,
                                            const long other_trip_id,
                                            const long other_position,
                                            const double other_departure_time) -> void {
        reset_other_schedule_to_reinsertion_time(initial_solution, new_solution, other_trip_id, other_position);
        set_trip_last_processed_position(other_trip_id, other_position - 1);
        increase_trip_reinsertions(other_trip_id);
        auto other_trip_departure = get_departure(other_departure_time, other_trip_id,
                                                  other_position, TRAVEL,
                                                  get_trip_reinsertions(other_trip_id));
        insert_departure_in_pq(other_trip_departure);
    }

    void Scheduler::mark_waiting_trips(Solution &initial_solution,
                                       const Solution &new_solution,
                                       double current_new_arrival,
                                       const Departure &departure) {
        for (long other_trip_id: get_trips_to_mark()) {
            if (check_mark_waiting_trip(initial_solution, other_trip_id, current_new_arrival, departure)) {
                long other_position = instance.get_arc_position_in_trip_route(departure.arc_id, other_trip_id);
                double other_departure_time = new_solution.get_trip_arc_departure(other_trip_id, other_position);
                mark_trip(other_trip_id, other_departure_time, other_position);
            }
        }
    }

    auto Scheduler::check_if_other_should_be_marked(const Solution &initial_solution,
                                                    const long other_trip_id,
                                                    const long other_position,
                                                    const bool current_conflicts_with_other,
                                                    const Departure &departure) -> MarkInstruction {

        // Fetch original schedule information
        auto other_original_departure = initial_solution.get_trip_arc_departure(other_trip_id, other_position);
        auto current_original_departure = initial_solution.get_trip_arc_departure(departure.trip_id,
                                                                                  departure.position);
        auto current_original_arrival = initial_solution.get_trip_arc_departure(departure.trip_id,
                                                                                departure.position + 1);

        // Determine original and current order relationships
        auto other_was_originally_first = check_if_other_was_first(
                other_trip_id, other_original_departure, current_original_departure, departure);

        auto other_overlapped_with_current = check_if_other_had_conflict_with_current(
                other_trip_id, other_original_departure, current_original_departure, current_original_arrival,
                departure);

        bool other_is_first_now = check_if_other_is_first(other_trip_id, other_original_departure,
                                                          departure);
        bool current_was_originally_first = !other_was_originally_first;
        bool current_is_first_now = !other_is_first_now;

        // Calculate key states
        bool other_always_first = other_was_originally_first && other_is_first_now;
        bool switch_other_with_current_order = current_was_originally_first && other_is_first_now;
        bool switch_current_with_other_order = other_was_originally_first && current_is_first_now;
        bool current_always_first = current_was_originally_first && current_is_first_now;

        // Determine mark instruction
        if (other_always_first) {
            return MarkInstruction::NOT_MARK;
        }

        if (switch_other_with_current_order) {
            if (!other_overlapped_with_current && !current_conflicts_with_other) {
                return MarkInstruction::NOT_MARK;
            }
            return MarkInstruction::MARK;
        }

        if (switch_current_with_other_order || current_always_first) {
            return MarkInstruction::WAIT;
        }

        throw std::invalid_argument("Check if other should be marked: undefined case");
    }


    auto Scheduler::check_mark_waiting_trip(Solution &initial_solution,
                                            const TripID other_trip_id,
                                            const double current_new_arrival,
                                            const Departure &departure) -> bool {
        // Fetch positions and timing details
        auto other_position = instance.get_arc_position_in_trip_route(departure.arc_id, other_trip_id);
        auto other_original_departure = initial_solution.get_trip_arc_departure(other_trip_id, other_position);
        auto other_original_arrival = initial_solution.get_trip_arc_departure(other_trip_id, other_position + 1);
        auto current_original_departure = initial_solution.get_trip_arc_departure(departure.trip_id,
                                                                                  departure.position);
        auto current_original_arrival = initial_solution.get_trip_arc_departure(departure.trip_id,
                                                                                departure.position + 1);

        // Check for conflicts between trips
        auto current_had_conflict_with_other = check_if_current_had_conflict_with_other(
                other_trip_id, other_original_departure, current_original_departure,
                other_original_arrival, departure
        );
        auto other_had_conflict_with_current = check_if_other_had_conflict_with_current(
                other_trip_id, other_original_departure, current_original_departure,
                current_original_arrival, departure
        );
        auto other_has_conflict_with_current = check_if_other_has_conflict_with_current(
                other_trip_id, other_original_departure, current_new_arrival, departure
        );

        // Determine the order of trips
        bool other_was_first = check_if_other_was_first(
                other_trip_id, other_original_departure, current_original_departure, departure
        );
        bool other_is_first = check_if_other_is_first(other_trip_id, other_original_departure, departure);

        // Logical flags for conditions
        bool current_did_not_conflict_with_other = !current_had_conflict_with_other;
        bool other_does_not_conflict_with_current = !other_has_conflict_with_current;
        bool current_was_first = !other_was_first;
        bool current_is_first = !other_is_first;

        // Evaluate conditions
        bool switch_current_with_other_order =
                (other_was_first && current_is_first) || (current_was_first && other_is_first);
        bool current_always_first = current_was_first && current_is_first;
        bool trips_conflicts_never = current_did_not_conflict_with_other && other_does_not_conflict_with_current;
        bool other_conflicts_always = other_had_conflict_with_current && other_has_conflict_with_current;

        // Decision logic
        if (switch_current_with_other_order) {
            return !trips_conflicts_never;
        } else if (current_always_first) {
            return !other_conflicts_always;
        } else {
            throw std::invalid_argument("Undefined case in check_mark_waiting_trip");
        }
    }


    auto Scheduler::mark_trip(const long other_trip_id,
                              const double other_departure_time,
                              const long other_position) -> void {
        auto other_departure = get_departure(other_departure_time,
                                             other_trip_id,
                                             other_position,
                                             ACTIVATION,
                                             0);
        set_trip_status(other_trip_id, STAGING);
        insert_departure_in_pq(other_departure);
    }
}
