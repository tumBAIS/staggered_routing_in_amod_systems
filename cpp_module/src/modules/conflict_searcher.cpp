#include <algorithm>
#include <iostream>
#include "scheduler.h"
#include "conflict_searcher.h"
#include <queue>

namespace cpp_module {

    auto compare_conflicts(const Conflict &a, const Conflict &b) -> bool {
        if (a.delayConflict > b.delayConflict) {
            return true;
        } else if (a.delayConflict == b.delayConflict) {
            return a.current_trip_id > b.current_trip_id;
        }
        return false;
    }

    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void {
        if (!conflicts_in_schedule.empty()) {
            std::sort(conflicts_in_schedule.begin(),
                      conflicts_in_schedule.end(),
                      compare_conflicts);
        }
    }

    auto compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc,
                                 const double &departure_time) -> double {
        auto vehicle_left_arc = !arrivals_on_arc.empty() && arrivals_on_arc.top().time <= departure_time;
        while (vehicle_left_arc) {
            arrivals_on_arc.pop();
            vehicle_left_arc = !arrivals_on_arc.empty() && arrivals_on_arc.top().time <= departure_time;
        }
        return static_cast<double>(arrivals_on_arc.size()) + 1.0;
    }

    auto compute_delay_on_arc(const double &vehicles_on_arc,
                              const Instance &arg_instance,
                              const long arc) -> double {
        if (arc == 0) {
            return 0.0;
        }
        std::vector<double> delays_at_pieces;
        delays_at_pieces.reserve(arg_instance.get_number_of_pieces_delay_function() + 1);

        double height_prev_piece = 0.0;
        delays_at_pieces.push_back(0.0);

        for (std::size_t i = 0; i < arg_instance.get_number_of_pieces_delay_function(); ++i) {
            const double threshold_capacity = arg_instance.get_piece_threshold(i) * arg_instance.get_arc_capacity(arc);
            const double slope = arg_instance.get_arc_travel_time(arc) * arg_instance.get_piece_slope(i) /
                                 arg_instance.get_arc_capacity(arc);

            if (vehicles_on_arc > threshold_capacity) {
                double delay_current_piece = height_prev_piece + slope * (vehicles_on_arc - threshold_capacity);
                delays_at_pieces.push_back(delay_current_piece);
            }

            if (i < arg_instance.get_number_of_pieces_delay_function() - 1) {
                double next_threshold_capacity =
                        arg_instance.get_piece_threshold(i + 1) * arg_instance.get_arc_capacity(arc);
                height_prev_piece += slope * (next_threshold_capacity - threshold_capacity);
            }
        }

        return *std::max_element(delays_at_pieces.begin(), delays_at_pieces.end());
    }

    auto
    ConflictSearcherNew::create_conflict(long arc, double delay, ConflictingArrival &sorted_arrival) const -> Conflict {
        return Conflict{
                arc,
                current_vehicle_info.trip_id,
                sorted_arrival.vehicle,
                delay,
                sorted_arrival.arrival - current_vehicle_info.departure_time + CONSTR_TOLERANCE,
                0.0,
                0.0
        };
    }

    auto ConflictSearcherNew::get_instructions_conflict(const VehicleSchedule &congested_schedule,
                                                        long other_position) -> InstructionsConflict {
        if (other_info.trip_id == current_vehicle_info.trip_id) {
            return InstructionsConflict::CONTINUE;
        }

        other_info.earliest_departure_time = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                           other_position);
        other_info.earliest_arrival_time = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                         other_position + 1);
        other_info.latest_departure_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                       other_position);
        other_info.latest_arrival_time = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                     other_position + 1);

        bool other_comes_before_and_cannot_overlap =
                other_info.latest_arrival_time <= current_vehicle_info.earliest_departure_time;
        bool other_comes_before_and_can_overlap =
                other_info.earliest_departure_time <= current_vehicle_info.earliest_departure_time &&
                current_vehicle_info.earliest_departure_time <= other_info.latest_arrival_time;
        bool other_comes_after_and_can_overlap =
                current_vehicle_info.earliest_departure_time <= other_info.earliest_departure_time &&
                other_info.earliest_departure_time <= current_vehicle_info.latest_departure_time;
        bool other_comes_after_and_cannot_overlap =
                other_info.earliest_departure_time >= current_vehicle_info.latest_departure_time;

        if (other_comes_before_and_cannot_overlap) {
            return InstructionsConflict::CONTINUE;
        } else if (other_comes_before_and_can_overlap || other_comes_after_and_can_overlap) {
            other_info.departure_time = congested_schedule[other_info.trip_id][other_position];
            other_info.arrival_time = congested_schedule[other_info.trip_id][other_position + 1];
            bool current_conflicts_with_other =
                    other_info.departure_time <= current_vehicle_info.departure_time &&
                    current_vehicle_info.departure_time < other_info.arrival_time;
            if (current_conflicts_with_other) {
                return InstructionsConflict::ADD_CONFLICT;
            }
            return InstructionsConflict::CONTINUE;
        } else if (other_comes_after_and_cannot_overlap) {
            return InstructionsConflict::BREAK;
        } else {
            throw std::invalid_argument("get_instructions_conflict: unspecified case!");
        }
    }

    auto ConflictSearcherNew::add_conflicts_to_conflict_list(std::vector<Conflict> &conflicts_list, long arc) -> void {
        std::sort(conflicting_arrivals.begin(), conflicting_arrivals.end(), compare_conflicting_arrivals);
        long vehicles_on_arc = 1;
        for (auto sorted_arrival: conflicting_arrivals) {
            vehicles_on_arc++;
            double conflict_delay = compute_delay_on_arc(vehicles_on_arc, instance, arc);
            {
                Conflict conflict = create_conflict(arc, conflict_delay, sorted_arrival);
                conflicts_list.push_back(conflict);
            }
        }
    }

    auto ConflictSearcherNew::update_current_vehicle_info(long current_vehicle,
                                                          const VehicleSchedule &congested_schedule,
                                                          long position) -> void {
        current_vehicle_info.trip_id = current_vehicle;
        current_vehicle_info.departure_time = congested_schedule[current_vehicle][position];
        current_vehicle_info.arrival_time = congested_schedule[current_vehicle][position + 1];
        current_vehicle_info.earliest_departure_time =
                instance.get_trip_arc_earliest_departure_time(current_vehicle, position);
        current_vehicle_info.latest_departure_time =
                instance.get_trip_arc_latest_departure_time(current_vehicle, position);
        current_vehicle_info.earliest_arrival_time =
                instance.get_trip_arc_earliest_departure_time(current_vehicle, position + 1);
        current_vehicle_info.latest_arrival_time =
                instance.get_trip_arc_latest_departure_time(current_vehicle, position + 1);
    }

    auto ConflictSearcherNew::check_vehicle_has_delay(const VehicleSchedule &congested_schedule,
                                                      long current_vehicle) -> bool {
        const double free_flow_travel_time_vehicle = instance.get_trip_free_flow_time(current_vehicle);
        const double congested_time_vehicle =
                congested_schedule[current_vehicle].back() - congested_schedule[current_vehicle].front();
        return congested_time_vehicle - free_flow_travel_time_vehicle > TOLERANCE;
    }

    auto ConflictSearcherNew::get_conflict_list(const VehicleSchedule &congested_schedule) -> std::vector<Conflict> {
        std::vector<Conflict> conflicts_list;
        for (auto current_vehicle = 0; current_vehicle < congested_schedule.size(); current_vehicle++) {
            bool vehicle_has_delay = check_vehicle_has_delay(congested_schedule, current_vehicle);
            if (vehicle_has_delay) {
                for (auto position = 0; position < congested_schedule[current_vehicle].size() - 1; position++) {
                    long arc = instance.get_arc_at_position_in_trip_route(current_vehicle, position);
                    double delay = congested_schedule[current_vehicle][position + 1] -
                                   congested_schedule[current_vehicle][position] -
                                   instance.get_arc_travel_time(arc);
                    if (delay > TOLERANCE) {
                        conflicting_arrivals.clear();
                        update_current_vehicle_info(current_vehicle, congested_schedule, position);
                        for (auto other_vehicle: instance.get_conflicting_set(arc)) {
                            other_info.trip_id = other_vehicle;
                            const long other_position = get_index(instance.get_trip_route(other_vehicle), arc);
                            auto instructions_conflict = get_instructions_conflict(congested_schedule, other_position);
                            if (instructions_conflict == InstructionsConflict::CONTINUE) {
                                continue;
                            } else if (instructions_conflict == InstructionsConflict::BREAK) {
                                break;
                            } else {
                                conflicting_arrival.arrival = other_info.arrival_time;
                                conflicting_arrival.vehicle = other_info.trip_id;
                                conflicting_arrivals.push_back(conflicting_arrival);
                            }
                        }
                        add_conflicts_to_conflict_list(conflicts_list, arc);
                    }
                }
            }
        }
        return conflicts_list;
    }
}
