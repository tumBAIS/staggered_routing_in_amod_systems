// Created by anton on 11/12/2024.

#include "scheduler.h"
#include "stdexcept"

namespace cpp_module {

// Helper function to check if a time comparison is within tolerance
    bool Scheduler::is_within_tolerance(double time1, double time2) {
        return std::abs(time1 - time2) <= TOLERANCE;
    }

// Helper function to determine if one trip comes before another
    bool
    Scheduler::comes_before(double earlier_time, double later_time, long earlier_trip_id, long later_trip_id) {
        return earlier_time < later_time - TOLERANCE ||
               (is_within_tolerance(earlier_time, later_time) && earlier_trip_id < later_trip_id);
    }

// Helper function to determine if one trip comes after another
    bool
    Scheduler::comes_after(double earlier_time, double later_time, long earlier_trip_id, long later_trip_id) {
        return earlier_time > later_time + TOLERANCE ||
               (is_within_tolerance(earlier_time, later_time) && earlier_trip_id > later_trip_id);
    }

// Main function using the helpers
    auto Scheduler::check_if_trips_within_conflicting_set_can_conflict(
            const long other_trip_id,
            const long other_position,
            const Departure &departure
    ) -> bool {

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
        bool other_comes_before_and_does_not_overlap = comes_before(
                other_latest_arrival_time,
                current_earliest_departure_time,
                other_trip_id,
                departure.trip_id
        );

        bool other_comes_before_and_overlaps =
                comes_before(
                        other_earliest_departure_time, current_earliest_departure_time, other_trip_id, departure.trip_id
                ) &&
                !comes_before(
                        other_latest_arrival_time, current_earliest_departure_time, other_trip_id, departure.trip_id
                );

        bool other_comes_after_and_overlaps =
                comes_after(
                        other_earliest_departure_time, current_earliest_departure_time, other_trip_id, departure.trip_id
                ) &&
                comes_before(
                        current_earliest_departure_time, other_latest_arrival_time, departure.trip_id, other_trip_id
                );

        bool other_comes_after_and_does_not_overlap = comes_after(
                other_earliest_departure_time,
                current_latest_arrival_time,
                other_trip_id,
                departure.trip_id
        );

        // Determine the appropriate instruction
        if (other_comes_before_and_does_not_overlap) {
            return false;
        } else if (other_comes_before_and_overlaps || other_comes_after_and_overlaps) {
            return true;
        } else if (other_comes_after_and_does_not_overlap) {
            set_break_flow_computation_flag(true);
            return false;
        } else {
            throw std::invalid_argument("Comparing vehicle bounds: undefined case!");
        }
    }


    auto Scheduler::get_flow_on_arc(Solution &initial_solution,
                                    Solution &new_solution,
                                    const Departure &departure) -> double {
        double flow_on_arc = 1.0;

        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (other_trip_id == departure.trip_id) {
                continue; // Skip the current trip
            }

            long other_position = instance.get_arc_position_in_trip_route(departure.arc_id, other_trip_id);
            Tie tie = {
                    departure.trip_id,
                    other_trip_id,
                    departure.position,
                    other_position,
                    departure.arc_id
            };

            if (check_tie(new_solution, tie)) {
                new_solution.set_ties_flag(true);
                return UNUSED_VALUE;
            }

            flow_on_arc += process_conflicting_trip(
                    initial_solution,
                    new_solution,
                    departure,
                    other_trip_id,
                    other_position
            );

            if (get_break_flow_computation_flag()) {
                set_break_flow_computation_flag(false);
                break;
            }
        }

        return flow_on_arc;
    }

    double Scheduler::process_conflicting_trip(Solution &initial_solution,
                                               Solution &new_solution,
                                               const Departure &departure,
                                               TripID other_trip_id,
                                               Position other_position) {
        if (!check_if_trips_within_conflicting_set_can_conflict(other_trip_id, other_position, departure)) {
            return 0.0;
        }

        bool other_vehicle_is_active = get_trip_status(other_trip_id) == ACTIVE;
        double other_departure_time = new_solution.get_trip_arc_departure(other_trip_id, other_position);
        double other_arrival = new_solution.get_trip_arc_departure(other_trip_id, other_position + 1);

        bool current_conflicts_with_other = check_conflict_with_other_vehicle(
                other_trip_id, other_departure_time, other_arrival, departure);

        if (!other_vehicle_is_active) {
            return handle_inactive_vehicle(
                    initial_solution, other_trip_id, other_position,
                    current_conflicts_with_other, departure
            );
        } else {
            return handle_active_vehicle(
                    initial_solution, new_solution, other_trip_id, other_position,
                    other_departure_time, current_conflicts_with_other, departure
            );
        }
    }


    double Scheduler::handle_inactive_vehicle(Solution &initial_solution,
                                              TripID other_trip_id,
                                              long other_position,
                                              bool current_conflicts_with_other,
                                              const Departure &departure) {
        double flow_increment = 0.0;

        if (current_conflicts_with_other) {
            flow_increment += 1.0;
        }

        MarkInstruction mark_instruction = check_if_other_should_be_marked(
                initial_solution, other_trip_id, other_position, current_conflicts_with_other, departure);

        if (mark_instruction == MARK) {
            mark_trip(other_trip_id, initial_solution.get_trip_arc_departure(other_trip_id, other_position),
                      other_position);
            set_lazy_update_pq_flag(true);
        } else if (mark_instruction == WAIT) {
            insert_trip_to_mark(other_trip_id);
        }

        return flow_increment;
    }

    double Scheduler::handle_active_vehicle(Solution &initial_solution,
                                            Solution &new_solution,
                                            TripID other_trip_id,
                                            long other_position,
                                            double other_departure_time,
                                            bool current_conflicts_with_other,
                                            const Departure &departure) {
        double flow_increment = 0.0;

        bool other_is_processed_on_this_arc =
                (other_position <= get_trip_last_processed_position(other_trip_id));

        bool other_is_first = check_if_other_is_first(
                other_trip_id, other_departure_time, departure);

        if (other_is_processed_on_this_arc) {
            if (!other_is_first) {
                reinsert_other_in_queue(initial_solution, new_solution, other_trip_id,
                                        other_position, other_departure_time);
                return 0.0;
            }

            if (current_conflicts_with_other) {
                flow_increment += 1.0;
            }
        }

        return flow_increment;
    }


    auto Scheduler::check_if_vehicle_is_late(const double current_vehicle_new_arrival,
                                             const Departure &departure) const -> bool {
        if (current_vehicle_new_arrival >
            instance.get_trip_arc_latest_departure_time(departure.trip_id, departure.position + 1)) {
            return true;
        }
        return false;
    }

    auto Scheduler::check_conflict_with_other_vehicle(const long other_trip_id,
                                                      const double other_departure,
                                                      const double other_arrival,
                                                      const Departure &departure) -> bool {
        // Check if there is a conflict using TOLERANCE
        bool current_conflicts_with_other =
                other_departure - TOLERANCE <= departure.time &&
                departure.time < other_arrival + TOLERANCE;

        // Handle tie-breaking when departure times are within TOLERANCE
        if (std::abs(other_departure - departure.time) <= TOLERANCE) {
            if (departure.trip_id < other_trip_id) {
                // Break tie in favor of the trip with the smaller trip_id
                return false;
            }
        }

        return current_conflicts_with_other;
    }

}
