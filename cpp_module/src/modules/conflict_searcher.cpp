#include <algorithm>
#include <iostream>
#include "scheduler.h"
#include "conflict_searcher.h"
#include <queue>

namespace cpp_module {

    auto compareConflicts(const Conflict &a, const Conflict &b) -> bool {
        if (a.delayConflict > b.delayConflict) {
            return true;
        } else if (a.delayConflict == b.delayConflict) {
            if (a.current_trip_id > b.current_trip_id) {
                return true;
            } else { return false; }
        } else {
            return false;
        }
    }


    auto _sortConflicts(std::vector<Conflict> &conflictsInSchedule) -> void {
        if (!conflictsInSchedule.empty()) {
            std::sort(conflictsInSchedule.begin(),
                      conflictsInSchedule.end(),
                      compareConflicts);
        }
    }


    auto compute_vehicles_on_arc(MinQueueDepartures &arrivalsOnArc, const double &departureTime) -> double {
        // Remove arrivals from the arc completed by departureTime time
        auto vehicleLeftArc = !arrivalsOnArc.empty() && arrivalsOnArc.top().time <= departureTime;
        while (vehicleLeftArc) {
            arrivalsOnArc.pop();
            vehicleLeftArc = !arrivalsOnArc.empty() && arrivalsOnArc.top().time <= departureTime;
        }
        return (double) arrivalsOnArc.size() + 1.0;
    }

    auto compute_delay_on_arc(const double &vehiclesOnArc,
                              const Instance &instance,
                              const long arc) -> double {
        if (arc == 0) {
            return 0;
        }
        std::vector<double> delays_at_pieces;
        delays_at_pieces.reserve(
                instance.get_number_of_pieces_delay_function() + 1); // Reserve space to avoid reallocations

        double height_prev_piece = 0;
        delays_at_pieces.push_back(0); // Initial delay for the first piece

        for (std::size_t i = 0; i < instance.get_number_of_pieces_delay_function(); ++i) {
            const double th_capacity = instance.get_piece_threshold(i) * instance.get_arc_capacity(arc);
            const double slope = instance.get_arc_travel_time(arc) * instance.get_piece_slope(i) /
                                 instance.get_arc_capacity(arc);

            if (vehiclesOnArc > th_capacity) {
                // avoid computing surely not max values
                double delay_current_piece = height_prev_piece + slope * (vehiclesOnArc - th_capacity);
                delays_at_pieces.push_back(delay_current_piece);
            }

            if (i < instance.get_number_of_pieces_delay_function() - 1) {
                double next_th_cap = instance.get_piece_threshold(i + 1) * instance.get_arc_capacity(arc);
                height_prev_piece += slope * (next_th_cap - th_capacity);
            }
        }

        return *std::max_element(delays_at_pieces.begin(), delays_at_pieces.end());
    }


    auto
    ConflictSearcherNew::_createConflictNew(long arc, double delay,
                                            ConflictingArrival &sortedArrival) const -> Conflict {
        Conflict conflict{};
        conflict.arc = arc;
        conflict.current_trip_id = currentVehicleInfo.trip_id;
        conflict.other_trip_id = sortedArrival.vehicle;
        conflict.delayConflict = delay;
        conflict.distanceToCover = sortedArrival.arrival - currentVehicleInfo.departureTime + CONSTR_TOLERANCE;
        conflict.staggeringCurrentVehicle = 0;
        conflict.destaggeringOtherVehicle = 0;
        return conflict;
    }


    auto
    ConflictSearcherNew::getInstructionsConflict(const VehicleSchedule &congestedSchedule,
                                                 long other_position) -> InstructionsConflict {
        if (other_info.trip_id == currentVehicleInfo.trip_id) {
            return InstructionsConflict::CONTINUE;
        }
        other_info.earliestDepartureTime = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                         other_position);
        other_info.earliestArrivalTime = instance.get_trip_arc_earliest_departure_time(other_info.trip_id,
                                                                                       other_position + 1);
        other_info.latestDepartureTime = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                     other_position);
        other_info.latestArrivalTime = instance.get_trip_arc_latest_departure_time(other_info.trip_id,
                                                                                   other_position + 1);

        bool otherComesBeforeAndCannotOverlap =
                other_info.latestArrivalTime <= currentVehicleInfo.earliestDepartureTime;
        bool otherComesBeforeAndCanOverlap =
                other_info.earliestDepartureTime <= currentVehicleInfo.earliestDepartureTime &&
                currentVehicleInfo.earliestDepartureTime <= other_info.latestArrivalTime;
        bool otherComesAfterAndCanOverlap =
                currentVehicleInfo.earliestDepartureTime <= other_info.earliestDepartureTime &&
                other_info.earliestDepartureTime <= currentVehicleInfo.latestDepartureTime;
        bool otherComesAfterAndCannotOverlap =
                other_info.earliestDepartureTime >= currentVehicleInfo.latestDepartureTime;

        if (otherComesBeforeAndCannotOverlap) {
            return InstructionsConflict::CONTINUE;
        } else if (otherComesBeforeAndCanOverlap || otherComesAfterAndCanOverlap) {
            other_info.departureTime = congestedSchedule[other_info.trip_id][other_position];
            other_info.arrivalTime = congestedSchedule[other_info.trip_id][other_position + 1];
            bool currentConflictsWithOther =
                    other_info.departureTime <= currentVehicleInfo.departureTime &&
                    currentVehicleInfo.departureTime < other_info.arrivalTime;
            if (currentConflictsWithOther) {
                return InstructionsConflict::ADD_CONFLICT;
            } else {
                return InstructionsConflict::CONTINUE;
            }
        } else if (otherComesAfterAndCannotOverlap) {
            return InstructionsConflict::BREAK;
        } else {
            throw std::invalid_argument("GETINSTRUCTIONCONFLICT_ERROR: unspecified case!");
        }
    }

    auto ConflictSearcherNew::addConflictsToConflictsList(std::vector<Conflict> &conflictsList, long arc) -> void {
        std::sort(conflictingArrivals.begin(), conflictingArrivals.end(), compareConflictingArrivals);
        long vehiclesOnArc = 1;
        for (auto sortedArrival: conflictingArrivals) {
            vehiclesOnArc++;
            double conflictDelay = compute_delay_on_arc(vehiclesOnArc, instance, arc);
//            if (conflictDelay > TOLERANCE)
            {
                Conflict conflict = _createConflictNew(arc, conflictDelay, sortedArrival);
                conflictsList.push_back(conflict);
            }
        }
    }

    auto ConflictSearcherNew::updateCurrentVehicleInfo(long currentVehicle,
                                                       const VehicleSchedule &congestedSchedule,
                                                       long position) -> void {
        currentVehicleInfo.trip_id = currentVehicle;
        currentVehicleInfo.departureTime = congestedSchedule[currentVehicle][position];
        currentVehicleInfo.arrivalTime = congestedSchedule[currentVehicle][position + 1];
        currentVehicleInfo.earliestDepartureTime = instance.get_trip_arc_earliest_departure_time(currentVehicle,
                                                                                                 position);
        currentVehicleInfo.latestDepartureTime = instance.get_trip_arc_latest_departure_time(currentVehicle, position);
        currentVehicleInfo.earliestArrivalTime = instance.get_trip_arc_earliest_departure_time(currentVehicle,
                                                                                               position + 1);
        currentVehicleInfo.latestArrivalTime = instance.get_trip_arc_latest_departure_time(currentVehicle,
                                                                                           position + 1);
    }

    auto
    ConflictSearcherNew::_checkIfVehicleHasDelay(const VehicleSchedule &congestedSchedule,
                                                 long currentVehicle) -> bool {
        const double ffTravelTimeVehicle = instance.get_trip_free_flow_time(currentVehicle);
        const double congestedTimeVehicle =
                congestedSchedule[currentVehicle].back() - congestedSchedule[currentVehicle].front();
        return congestedTimeVehicle - ffTravelTimeVehicle > TOLERANCE;
    }

    auto ConflictSearcherNew::getConflictsListNew(const VehicleSchedule &congestedSchedule) -> std::vector<Conflict> {

        std::vector<Conflict> conflictsList;
        for (auto currentVehicle = 0; currentVehicle < congestedSchedule.size(); currentVehicle++) {
            auto vehicleHasDelay = _checkIfVehicleHasDelay(congestedSchedule, currentVehicle);
            if (vehicleHasDelay) {
                for (auto position = 0; position < congestedSchedule[currentVehicle].size() - 1; position++) {
                    long arc = instance.get_arc_at_position_in_trip_route(currentVehicle, position);
                    double delay = congestedSchedule[currentVehicle][position + 1] -
                                   congestedSchedule[currentVehicle][position] -
                                   instance.get_arc_travel_time(arc);
                    if (delay > TOLERANCE) {
                        conflictingArrivals.clear();
                        updateCurrentVehicleInfo(currentVehicle, congestedSchedule, position);
                        for (auto otherVehicle: instance.get_conflicting_set(arc)) {
                            other_info.trip_id = otherVehicle;
                            const long otherPosition = get_index(instance.get_trip_route(otherVehicle), arc);
                            auto instructionsConflict = getInstructionsConflict(congestedSchedule, otherPosition);
                            if (instructionsConflict == CONTINUE) {
                                continue;
                            } else if (instructionsConflict == BREAK) {
                                break;
                            } else {
                                conflictingArrival.arrival = other_info.arrivalTime;
                                conflictingArrival.vehicle = other_info.trip_id;
                                conflictingArrivals.push_back(conflictingArrival);
                            }
                        }
                        addConflictsToConflictsList(conflictsList, arc);
                    }
                }
            }
        }
        return conflictsList;
    }
}