// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::check_if_trips_within_conflicting_set_can_conflict(
            const long other_trip_id,
            const long other_position
    ) const -> InstructionConflictingSet {
        // Assumption: The trips in the conflicting set are ordered by ascending earliest departure time.

        // Fetch the earliest departure and latest arrival times for the current trip
        double current_earliest_departure_time = instance.get_trip_arc_earliest_departure_time(
                departure.trip_id, departure.position
        );
        double current_latest_arrival_time = instance.get_trip_arc_latest_departure_time(
                departure.trip_id, departure.position + 1
        );

        // Fetch the earliest departure and latest arrival times for the other trip
        double other_earliest_departure_time = instance.get_trip_arc_earliest_departure_time(
                other_trip_id, other_position
        );
        double other_latest_arrival_time = instance.get_trip_arc_latest_departure_time(
                other_trip_id, other_position + 1
        );

        // Determine overlap conditions
        bool other_comes_before_and_does_not_overlap =
                other_latest_arrival_time < current_earliest_departure_time;

        bool other_comes_before_and_overlaps =
                other_earliest_departure_time <= current_earliest_departure_time &&
                current_earliest_departure_time < other_latest_arrival_time;

        bool other_comes_after_and_overlaps =
                current_earliest_departure_time <= other_earliest_departure_time &&
                other_earliest_departure_time < current_latest_arrival_time;

        bool other_comes_after_and_does_not_overlap =
                other_earliest_departure_time > current_latest_arrival_time;

        // Determine the appropriate instruction
        if (other_comes_before_and_does_not_overlap) {
            return CONTINUE;
        } else if (other_comes_before_and_overlaps || other_comes_after_and_overlaps) {
            return EVALUATE;
        } else if (other_comes_after_and_does_not_overlap) {
            return BREAK;
        } else {
            throw std::invalid_argument("Comparing vehicle bounds: undefined case!");
        }
    }

    auto Scheduler::update_vehicles_on_arc_of_conflicting_set(Solution &solution,
                                                              double &vehicles_on_arc) -> void {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (other_trip_id == departure.trip_id) {
                continue;
            }
            const long other_position = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
            const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
                    other_trip_id, other_position);
            if (instruction == CONTINUE) {
                continue;
            } else if (instruction == BREAK) {
                break;
            }

            const bool other_vehicle_is_active = trip_status_list[other_trip_id] == ACTIVE;
            const bool other_vehicle_is_not_active = !other_vehicle_is_active;
            const double other_departure = solution.get_trip_arc_departure(other_trip_id, other_position);
            const double other_arrival = solution.get_trip_arc_departure(other_trip_id, other_position + 1);
            const bool current_conflicts_with_other = check_conflict_with_other_vehicle(other_trip_id,
                                                                                        other_departure,
                                                                                        other_arrival);
            if (other_vehicle_is_not_active) {
                if (current_conflicts_with_other) { vehicles_on_arc++; }
                VehicleShouldBeMarked should_mark = check_if_other_should_be_marked(other_trip_id,
                                                                                    other_position,
                                                                                    current_conflicts_with_other);
                if (should_mark == YES) {
                    mark_vehicle(other_trip_id, other_departure, other_position); // O(log n) -> pq.push
                    lazy_update_pq = true; //marked vehicle starting before
                    assert_lazy_update_is_necessary(other_departure);
                    print_lazy_update_priority_queue();
                } else if (should_mark == MAYBE) {
                    vehicles_to_mark.push_back(other_trip_id);
                }
            } else if (other_vehicle_is_active) {
                bool other_is_processed_on_this_arc = other_position <= last_processed_position[other_trip_id];
                const bool other_is_first = check_if_other_is_first_in_current_schedule(other_trip_id, other_departure);
                const bool other_is_not_first = !other_is_first;
                if (other_is_processed_on_this_arc) {
                    if (other_is_not_first) {
                        reinsert_other_in_queue(solution, other_trip_id, other_position, other_departure,
                                                departure.arc_id);
                        continue;
                    }
                    if (current_conflicts_with_other) {
                        vehicles_on_arc++;
                    }
                }
                assert_other_starts_after_if_has_to_be_processed_on_this_arc_next(other_trip_id, other_position,
                                                                                  other_departure);
            }
        }
    }

    auto Scheduler::check_if_tie_in_set(const VehicleSchedule &congested_schedule) -> bool {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (departure.trip_id != other_trip_id) {
                const long other_position = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
                        other_trip_id, other_position);
                if (instruction == CONTINUE) {
                    continue;
                } else if (instruction == BREAK) {
                    break;
                }
                Tie tie = {departure.trip_id,
                           other_trip_id,
                           departure.position,
                           other_position,
                           departure.arc_id};
                bool tie_on_arc = check_if_vehicles_have_tie(congested_schedule, tie);
                if (tie_on_arc) {
                    return true;
                }
            }
        }
        return false;
    }

    auto Scheduler::check_if_vehicle_is_late(const double current_vehicle_new_arrival) const -> bool {
        if (current_vehicle_new_arrival >
            instance.get_trip_arc_latest_departure_time(departure.trip_id, departure.position + 1)) {
            return true;
        }
        return false;
    }

    auto Scheduler::check_conflict_with_other_vehicle(const long other_vehicle,
                                                      const double other_departure,
                                                      const double other_arrival) const -> bool {
        // Given the change, check if vehicle conflict
        bool current_conflicts_with_other = other_departure <= departure.time && departure.time < other_arrival;
        if (other_departure == departure.time) {
            if (departure.trip_id < other_vehicle) {
                // Correctly break tie
                return false;
            }
        }
        return current_conflicts_with_other;
    }
}
