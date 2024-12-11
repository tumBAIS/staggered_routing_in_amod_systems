//
// Created by anton on 11/12/2024.
//


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
                                                              double &vehiclesOnArc) -> void {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (other_trip_id == departure.trip_id) {
                continue;
            }
            const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
            const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
                    other_trip_id, otherPosition);
            if (instruction == CONTINUE) {
                continue;
            } else if (instruction == BREAK) {
                break;
            }

            const bool otherVehicleIsActive = trip_status_list[other_trip_id] == ACTIVE;
            const bool otherVehicleIsNotActive = !otherVehicleIsActive;
            const double otherDeparture = solution.get_trip_arc_departure(other_trip_id, otherPosition);
            const double otherArrival = solution.get_trip_arc_departure(other_trip_id, otherPosition + 1);
            const bool currentConflictsWithOther = check_conflict_with_other_vehicle(other_trip_id,
                                                                                     otherDeparture,
                                                                                     otherArrival);
            if (otherVehicleIsNotActive) {
                if (currentConflictsWithOther) { vehiclesOnArc++; }
                vehicleShouldBeMarked shouldMark = check_if_other_should_be_marked(other_trip_id,
                                                                                   otherPosition,
                                                                                   currentConflictsWithOther);
                if (shouldMark == YES) {
                    mark_vehicle(other_trip_id, otherDeparture, otherPosition); // O(log n) -> pq.push
                    lazy_update_pq = true; //marked vehicle starting before
                    _assertLazyUpdateIsNecessary(otherDeparture);
                    printLazyUpdatePriorityQueue();
                } else if (shouldMark == MAYBE) {
                    vehicles_to_mark.push_back(other_trip_id);
                }
            } else if (otherVehicleIsActive) {
                bool otherIsProcessedOnThisArc = otherPosition <= last_processed_position[other_trip_id];
                const bool otherIsFirst = check_if_other_is_first_in_current_schedule(other_trip_id, otherDeparture);
                const bool otherIsNotFirst = !otherIsFirst;
                if (otherIsProcessedOnThisArc) {
                    if (otherIsNotFirst) {
                        reinsert_other_in_queue(solution, other_trip_id, otherPosition, otherDeparture,
                                                departure.arc_id);
                        continue;
                    }
                    if (currentConflictsWithOther) {
                        vehiclesOnArc++;
                    }
                }
                _assertOtherStartsAfterIfHasToBeProcessedOnThisArcNext(other_trip_id, otherPosition, otherDeparture);
            }
        }
    }

    auto Scheduler::check_if_tie_in_set(const VehicleSchedule &congestedSchedule) -> bool {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (departure.trip_id != other_trip_id) {
                const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
                        other_trip_id, otherPosition);
                if (instruction == CONTINUE) {
                    continue;
                } else if (instruction == BREAK) {
                    break;
                }
                Tie tie = {departure.trip_id,
                           other_trip_id,
                           departure.position,
                           otherPosition,
                           departure.arc_id};
                bool tieOnArc = check_if_vehicles_have_tie(congestedSchedule, tie);
                if (tieOnArc) {
                    return true;
                }
            }
        }
        return false;
    }

    auto Scheduler::check_if_vehicle_is_late(const double currentVehicleNewArrival) const -> bool {
        if (currentVehicleNewArrival >
            instance.get_trip_arc_latest_departure_time(departure.trip_id, departure.position + 1)) {
            return true;
        }
        return false;
    }

    auto Scheduler::check_conflict_with_other_vehicle(const long otherVehicle,
                                                      const double otherDeparture,
                                                      const double otherArrival) const -> bool {
        // given the change, check if vehicle conflict
        bool currentConflictsWithOther = otherDeparture <= departure.time && departure.time < otherArrival;
        if (otherDeparture == departure.time) {
            if (departure.trip_id < otherVehicle) {
                // correctly break tie
                return false;
            }
        }
        return currentConflictsWithOther;
    }
}