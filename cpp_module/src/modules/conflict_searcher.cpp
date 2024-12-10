#include <algorithm>
#include <iostream>
#include <queue>
#include "scheduler.h"
#include "conflict_searcher.h"

namespace cpp_module {

// Compare two conflicts for sorting
    auto compare_conflicts(const Conflict &a, const Conflict &b) -> bool {
        if (a.delayConflict > b.delayConflict) {
            return true;
        } else if (a.delayConflict == b.delayConflict) {
            return a.current_trip_id > b.current_trip_id;
        }
        return false;
    }

// Sort conflicts in the schedule
    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void {
        if (!conflicts_in_schedule.empty()) {
            std::sort(conflicts_in_schedule.begin(), conflicts_in_schedule.end(), compare_conflicts);
        }
    }

// Compute the number of vehicles on an arc at a given time
    auto compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc, const double &departure_time) -> double {
        // Remove arrivals completed by the departure time
        while (!arrivals_on_arc.empty() && arrivals_on_arc.top().time <= departure_time) {
            arrivals_on_arc.pop();
        }
        return static_cast<double>(arrivals_on_arc.size() + 1);
    }

// Compute the delay on an arc given the number of vehicles
    auto compute_delay_on_arc(const double &vehicles_on_arc, const Instance &instance, const long arc) -> double {
        if (arc == 0) {
            return 0;
        }

        std::vector<double> delays_at_pieces(instance.get_number_of_pieces_delay_function() + 1, 0);
        double height_prev_piece = 0;

        for (std::size_t i = 0; i < instance.get_number_of_pieces_delay_function(); ++i) {
            double threshold_capacity = instance.get_piece_threshold(i) * instance.get_arc_capacity(arc);
            double slope =
                    instance.get_arc_travel_time(arc) * instance.get_piece_slope(i) / instance.get_arc_capacity(arc);

            if (vehicles_on_arc > threshold_capacity) {
                double delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - threshold_capacity);
                delays_at_pieces[i] = delay_current_piece;
            }

            if (i < instance.get_number_of_pieces_delay_function() - 1) {
                double next_threshold_capacity = instance.get_piece_threshold(i + 1) * instance.get_arc_capacity(arc);
                height_prev_piece += slope * (next_threshold_capacity - threshold_capacity);
            }
        }

        return *std::max_element(delays_at_pieces.begin(), delays_at_pieces.end());
    }

// Create a conflict object
    auto
    ConflictSearcherNew::create_conflict(long arc, double delay,
                                         const ConflictingArrival &sorted_arrival) const -> Conflict {
        return {
                arc,
                current_vehicle_info.trip_id,
                sorted_arrival.vehicle,
                delay,
                sorted_arrival.arrival - current_vehicle_info.departure_time + CONSTR_TOLERANCE,
                0,
                0
        };
    }

// Determine conflict instructions between vehicles
    auto ConflictSearcherNew::get_conflict_instructions(const VehicleSchedule &congested_schedule,
                                                        long other_position) -> InstructionsConflict {
        if (other_info.trip_id == current_vehicle_info.trip_id) {
            return InstructionsConflict::CONTINUE;
        }

        // Update other vehicle's timing information
        other_info.earliest_departure_time = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                           other_position);

        other_info.latest_departure_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                       other_position);
        other_info.latest_arrival_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                     other_position + 1);

        bool other_before_no_overlap = other_info.latest_arrival_time <= current_vehicle_info.earliest_departure_time;
        bool other_before_overlap =
                other_info.earliest_departure_time <= current_vehicle_info.earliest_departure_time &&
                current_vehicle_info.earliest_departure_time <= other_info.latest_arrival_time;
        bool other_after_overlap = current_vehicle_info.earliest_departure_time <= other_info.earliest_departure_time &&
                                   other_info.earliest_departure_time <= current_vehicle_info.latest_departure_time;
        bool other_after_no_overlap = other_info.earliest_departure_time >= current_vehicle_info.latest_departure_time;

        if (other_before_no_overlap) {
            return InstructionsConflict::CONTINUE;
        } else if (other_before_overlap || other_after_overlap) {
            other_info.departure_time = congested_schedule[other_info.trip_id][other_position];
            other_info.arrival_time = congested_schedule[other_info.trip_id][other_position + 1];

            bool conflict_detected = other_info.departure_time <= current_vehicle_info.departure_time &&
                                     current_vehicle_info.departure_time < other_info.arrival_time;

            return conflict_detected ? InstructionsConflict::ADD_CONFLICT : InstructionsConflict::CONTINUE;
        } else if (other_after_no_overlap) {
            return InstructionsConflict::BREAK;
        }

        throw std::invalid_argument("Unexpected case in conflict instructions.");
    }

// Add conflicts for a specific arc to the conflicts list
    auto ConflictSearcherNew::add_conflicts_to_list(std::vector<Conflict> &conflicts_list, long arc) -> void {
        std::sort(conflicting_arrivals.begin(), conflicting_arrivals.end(), compare_conflicting_arrivals);

        long vehicles_on_arc = 1;
        for (const auto &arrival: conflicting_arrivals) {
            vehicles_on_arc++;
            double delay = compute_delay_on_arc(vehicles_on_arc, instance, arc);
            conflicts_list.push_back(create_conflict(arc, delay, arrival));
        }
    }

// Update current vehicle's timing information
    auto ConflictSearcherNew::update_current_vehicle_info(
            long current_vehicle,
            const VehicleSchedule &congested_schedule,
            long position
    ) -> void {
        current_vehicle_info.trip_id = current_vehicle;
        current_vehicle_info.departure_time = congested_schedule[current_vehicle][position];
        current_vehicle_info.arrival_time = congested_schedule[current_vehicle][position + 1];
        current_vehicle_info.earliest_departure_time = instance.get_trip_arc_earliest_departure_time(current_vehicle,
                                                                                                     position);
        current_vehicle_info.latest_departure_time = instance.get_trip_arc_latest_departure_time(current_vehicle,
                                                                                                 position);
        current_vehicle_info.latest_arrival_time = instance.get_trip_arc_latest_departure_time(current_vehicle,
                                                                                               position + 1);
    }


// Check if a vehicle has experienced delays
    auto
    ConflictSearcherNew::check_vehicle_delay(const VehicleSchedule &congested_schedule, long current_vehicle) -> bool {
        double free_flow_time = instance.get_trip_free_flow_time(current_vehicle);
        double congested_time =
                congested_schedule[current_vehicle].back() - congested_schedule[current_vehicle].front();
        return congested_time - free_flow_time > TOLERANCE;
    }

// Generate a list of conflicts for the given schedule
    auto ConflictSearcherNew::get_conflicts_list(const VehicleSchedule &congested_schedule) -> std::vector<Conflict> {
        std::vector<Conflict> conflicts_list;

        for (long current_vehicle = 0;
             current_vehicle < static_cast<long>(congested_schedule.size()); ++current_vehicle) {
            if (!check_vehicle_delay(congested_schedule, current_vehicle)) {
                continue;
            }

            for (long position = 0;
                 position < static_cast<long>(congested_schedule[current_vehicle].size()) - 1; ++position) {
                long arc = instance.get_arc_at_position_in_trip_route(current_vehicle, position);
                double delay = congested_schedule[current_vehicle][position + 1] -
                               congested_schedule[current_vehicle][position] -
                               instance.get_arc_travel_time(arc);

                if (delay > TOLERANCE) {
                    conflicting_arrivals.clear();
                    update_current_vehicle_info(current_vehicle, congested_schedule, position);

                    for (auto other_vehicle: instance.get_conflicting_set(arc)) {
                        long other_position = get_index(instance.get_trip_route(other_vehicle), arc);
                        auto instruction = get_conflict_instructions(congested_schedule, other_position);

                        if (instruction == InstructionsConflict::CONTINUE) {
                            continue;
                        } else if (instruction == InstructionsConflict::BREAK) {
                            break;
                        } else {
                            conflicting_arrivals.push_back({other_vehicle, other_info.arrival_time});
                        }
                    }

                    add_conflicts_to_list(conflicts_list, arc);
                }
            }
        }

        return conflicts_list;
    }

} // namespace cpp_module
