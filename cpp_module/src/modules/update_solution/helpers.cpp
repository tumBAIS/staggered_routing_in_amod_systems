// Created by anton on 11/12/2024.

#include <queue>
#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::reset_other_schedule_to_reinsertion_time(Solution &solution,
                                                             const long other_vehicle,
                                                             const long other_position) -> void {
        long steps_back = last_processed_position[other_vehicle] - other_position;
        for (auto step = 0; step < steps_back; step++) {
            solution.set_trip_arc_departure(other_vehicle, other_position + step + 1,
                                            original_schedule[other_vehicle][other_position +
                                                                             step + 1]);
        }
    }

    auto Scheduler::process_conflicting_set(Solution &complete_solution,
                                            double &delay,
                                            double &current_vehicle_new_arrival,
                                            double &vehicles_on_arc) -> void {
        update_vehicles_on_arc_of_conflicting_set(complete_solution, vehicles_on_arc);
        if (lazy_update_pq) { return; }
        tie_found = check_if_tie_in_set(complete_solution.get_schedule());
        if (tie_found) {
            return;
        }
        delay = compute_delay_on_arc(vehicles_on_arc, instance, departure.arc_id);
        print_delay_computed(delay);
        current_vehicle_new_arrival = departure.time + delay + instance.get_arc_travel_time(departure.arc_id);
        trip_is_late = check_if_vehicle_is_late(current_vehicle_new_arrival);
        if (trip_is_late) {
            return;
        }
        decide_on_vehicles_maybe_to_mark(complete_solution.get_schedule(), current_vehicle_new_arrival);
    }

    bool is_conf_set_empty(const std::vector<long> &conf_set) {
        return conf_set.empty();
    }

    auto Scheduler::process_vehicle(Solution &complete_solution) -> void {
        double current_vehicle_new_arrival = departure.time + instance.get_arc_travel_time(departure.arc_id);
        double vehicles_on_arc = 1;
        double delay = 0;
        const bool conf_set_is_empty = is_conf_set_empty(instance.get_conflicting_set(departure.arc_id));
        if (!conf_set_is_empty) {
            process_conflicting_set(complete_solution, delay, current_vehicle_new_arrival, vehicles_on_arc);
            if (lazy_update_pq || tie_found || trip_is_late) {
                return;
            }
        }
        assert_vehicles_on_arc_is_correct(vehicles_on_arc, complete_solution.get_schedule());
        update_vehicle_schedule(complete_solution, current_vehicle_new_arrival);
        assert_event_pushed_to_queue_is_correct();
        move_vehicle_forward_in_the_queue(current_vehicle_new_arrival); // O(2 * log n) - pq.push
    }

    auto Scheduler::check_if_other_is_first_in_original_schedule(const long other_vehicle,
                                                                 const double other_original_departure,
                                                                 const double current_original_departure) const -> bool {
        bool other_is_first_in_original_schedule = other_original_departure <= current_original_departure;
        if (other_original_departure == current_original_departure) {
            if (departure.trip_id < other_vehicle) {
                // Current vehicle would pass first - break tie
                other_is_first_in_original_schedule = false;
            }
        }
        return other_is_first_in_original_schedule;
    }

    auto Scheduler::check_if_other_is_first_in_current_schedule(const long other_vehicle,
                                                                const double other_original_departure) const -> bool {
        bool other_is_first_now = other_original_departure <= departure.time;
        if (departure.time == other_original_departure) {
            if (departure.trip_id < other_vehicle) {
                // Current vehicle would pass first - break tie
                other_is_first_now = false;
            }
        }
        return other_is_first_now;
    }

    auto Scheduler::check_if_current_overlapped_with_other(const long other_vehicle,
                                                           const double other_original_departure,
                                                           const double current_original_departure,
                                                           const double other_original_arrival) const -> bool {
        bool current_overlapped_with_other =
                other_original_departure <= current_original_departure &&
                current_original_departure < other_original_arrival;
        if (current_original_departure == other_original_departure) {
            if (departure.trip_id < other_vehicle) {
                current_overlapped_with_other = false;
            }
        }
        return current_overlapped_with_other;
    }

    auto Scheduler::check_if_other_overlapped_with_current(const long other_vehicle,
                                                           const double other_original_departure,
                                                           const double current_original_departure,
                                                           const double current_original_arrival) const -> bool {
        bool other_overlapped_with_current =
                current_original_departure <= other_original_departure &&
                other_original_departure < current_original_arrival;
        if (current_original_departure == other_original_departure) {
            if (other_vehicle < departure.trip_id) {
                other_overlapped_with_current = false;
            }
        }
        return other_overlapped_with_current;
    }

    auto Scheduler::check_if_other_overlaps_now_with_current(const long other_vehicle,
                                                             const double other_original_departure,
                                                             const double current_vehicle_new_arrival) const -> bool {
        bool other_overlaps_now_with_current =
                departure.time <= other_original_departure &&
                other_original_departure < current_vehicle_new_arrival;
        if (departure.time == other_original_departure) {
            if (other_vehicle < departure.trip_id) {
                other_overlaps_now_with_current = false;
            }
        }
        return other_overlaps_now_with_current;
    }

    auto Scheduler::check_conditions_to_mark(const bool switch_current_with_other_order,
                                             const bool vehicles_never_overlapped,
                                             const bool current_always_first,
                                             const bool other_always_overlaps) -> bool {
        // In order the conditions TO NOT MARK are:
        // 1. Other vehicle was always coming before (already checked) OR
        // 2. Other vehicle saw current vehicle as unit of flow, and still sees it as unit of flow OR
        // 3. Vehicles never saw each other as units of flow

        if (switch_current_with_other_order) {
            if (vehicles_never_overlapped) {
                return false;
            } else {
                return true;
            }
        } else if (current_always_first) {
            if (other_always_overlaps) {
                return false;
            } else {
                return true;
            }
        } else {
            throw std::invalid_argument("undefined case second function marking ");
        }
    }

    auto Scheduler::move_vehicle_forward_in_the_queue(const double current_vehicle_new_arrival) -> void {
        print_update_greatest_time_analyzed();
        departure.time = current_vehicle_new_arrival;
        last_processed_position[departure.trip_id] = departure.position;
        departure.position++;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
        pq_departures.push(departure);
        print_departure_pushed_to_queue();
    }

}