#include "scheduler.h"
#include <queue>
#include "stdexcept"

namespace cpp_module {


    auto Scheduler::reset_other_schedule_to_reinsertion_time(Solution &solution,
                                                             const long otherVehicle,
                                                             const long otherPosition) -> void {

        long stepsBack = last_processed_position[otherVehicle] - otherPosition;
        for (auto step = 0; step < stepsBack; step++) {
            solution.set_trip_arc_departure(otherVehicle, otherPosition + step + 1,
                                            original_schedule[otherVehicle][otherPosition +
                                                                            step + 1]);
        }
    }


    auto Scheduler::process_conflicting_set(Solution &completeSolution,
                                            double &delay,
                                            double &currentVehicleNewArrival,
                                            double &vehiclesOnArc) -> void {
        update_vehicles_on_arc_of_conflicting_set(completeSolution, vehiclesOnArc);
        if (lazy_update_pq) { return; }
        tie_found = check_if_tie_in_set(completeSolution.get_schedule());
        if (tie_found) {
            return;
        }
        delay = compute_delay_on_arc(vehiclesOnArc, instance, departure.arc_id);
        printDelayComputed(delay);
        currentVehicleNewArrival = departure.time + delay + instance.get_arc_travel_time(departure.arc_id);
        trip_is_late = check_if_vehicle_is_late(currentVehicleNewArrival);
        if (trip_is_late) {
            return;
        }
        decide_on_vehicles_maybe_to_mark(completeSolution.get_schedule(), currentVehicleNewArrival);

    }

    bool is_conf_set_empty(const std::vector<long> &confSet) {
        return confSet.empty();
    }

    auto Scheduler::process_vehicle(Solution &completeSolution) -> void {
        double currentVehicleNewArrival = departure.time + instance.get_arc_travel_time(departure.arc_id);
        double vehiclesOnArc = 1;
        double delay = 0;
        const bool confSetIsEmpty = is_conf_set_empty(instance.get_conflicting_set(departure.arc_id));
        if (!confSetIsEmpty) {
            process_conflicting_set(completeSolution, delay, currentVehicleNewArrival, vehiclesOnArc);
            if (lazy_update_pq || tie_found || trip_is_late) {
                return;
            }
        }
        _assertVehiclesOnArcIsCorrect(vehiclesOnArc, completeSolution.get_schedule());
        update_vehicle_schedule(completeSolution, currentVehicleNewArrival);
        _assertEventPushedToQueueIsCorrect();
        move_vehicle_forward_in_the_queue(currentVehicleNewArrival); // O(2 * log n) - pq.push
    }


    auto Scheduler::check_if_other_is_first_in_original_schedule(const long otherVehicle,
                                                                 const double otherOriginalDeparture,
                                                                 const double currentOriginalDeparture) const -> bool {
        bool otherIsFirstInOriginalSchedule = otherOriginalDeparture <= currentOriginalDeparture;
        if (otherOriginalDeparture == currentOriginalDeparture) {
            if (departure.trip_id < otherVehicle) {
                // current vehicle would pass first - break tie
                otherIsFirstInOriginalSchedule = false;
            }
        }
        return otherIsFirstInOriginalSchedule;
    }


    auto Scheduler::check_if_other_is_first_in_current_schedule(const long otherVehicle,
                                                                const double otherOriginalDeparture) const -> bool {
        bool otherIsFirstNow = otherOriginalDeparture <= departure.time;
        if (departure.time == otherOriginalDeparture) {
            if (departure.trip_id < otherVehicle) {
                // current vehicle would pass first - break tie
                otherIsFirstNow = false;
            }
        }
        return otherIsFirstNow;
    }


    auto Scheduler::check_if_current_overlapped_with_other(const long otherVehicle,
                                                           const double otherOriginalDeparture,
                                                           const double currentOriginalDeparture,
                                                           const double otherOriginalArrival) const -> bool {
        bool currentOverlappedWithOther =
                otherOriginalDeparture <= currentOriginalDeparture &&
                currentOriginalDeparture < otherOriginalArrival;
        if (currentOriginalDeparture == otherOriginalDeparture) {
            if (departure.trip_id < otherVehicle) {
                currentOverlappedWithOther = false;
            }
        }
        return currentOverlappedWithOther;
    }

    auto Scheduler::check_if_other_overlapped_with_current(const long otherVehicle,
                                                           const double otherOriginalDeparture,
                                                           const double currentOriginalDeparture,
                                                           const double currentOriginalArrival) const -> bool {
        bool otherOverlappedWithCurrent =
                currentOriginalDeparture <= otherOriginalDeparture &&
                otherOriginalDeparture < currentOriginalArrival;
        if (currentOriginalDeparture == otherOriginalDeparture) {
            if (otherVehicle < departure.trip_id) {
                otherOverlappedWithCurrent = false;
            }
        }
        return otherOverlappedWithCurrent;
    }

    auto Scheduler::check_if_other_overlaps_now_with_current(const long otherVehicle,
                                                             const double otherOriginalDeparture,
                                                             const double currentVehicleNewArrival) const -> bool {
        bool otherOverlapsNowWithCurrent =
                departure.time <= otherOriginalDeparture &&
                otherOriginalDeparture < currentVehicleNewArrival;
        if (departure.time == otherOriginalDeparture) {
            if (otherVehicle < departure.trip_id) {
                otherOverlapsNowWithCurrent = false;
            }
        }
        return otherOverlapsNowWithCurrent;
    }

    auto Scheduler::check_conditions_to_mark(const bool switchCurrentWithOtherOrder,
                                             const bool vehiclesNeverOverlapped,
                                             const bool currentAlwaysFirst,
                                             const bool otherAlwaysOverlaps) -> bool {
        // in order the conditions TO NOT MARK are:
        // 1.other vehicle was always coming before (already checked) OR
        // 2.other vehicle saw current vehicle as unit of flow, and still sees it as unit of flow OR
        // 3.vehicles never saw each other as units of flow

        if (switchCurrentWithOtherOrder) {
            if (vehiclesNeverOverlapped) {
                return false;
            } else {
                return true;
            }
        } else if (currentAlwaysFirst) {
            if (otherAlwaysOverlaps) {
                return false;
            } else {
                return true;
            }
        } else {
            throw std::invalid_argument("undefined case second function marking ");
        }
    }


    auto Scheduler::move_vehicle_forward_in_the_queue(const double currentVehicleNewArrival) -> void {
        _printUpdateGreatestTimeAnalyzed();
        departure.time = currentVehicleNewArrival;
        last_processed_position[departure.trip_id] = departure.position;
        departure.position++;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
        pq_departures.push(departure);
        _printDeparturePushedToQueue();
    }


}
