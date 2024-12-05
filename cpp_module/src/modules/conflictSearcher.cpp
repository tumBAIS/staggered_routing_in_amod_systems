#include <algorithm>
#include <iostream>
#include "module.h"
#include <queue>
#include <utility>
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

namespace cpp_module {

    auto compareConflicts(const Conflict &a, const Conflict &b) -> bool {
        if (a.delayConflict > b.delayConflict) {
            return true;
        } else if (a.delayConflict == b.delayConflict) {
            if (a.currentVehicle > b.currentVehicle) {
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


    auto computeVehiclesOnArc(MinQueueDepartures &arrivalsOnArc, const double &departureTime) -> double {
        // Remove arrivals from the arc completed by departureTime time
        auto vehicleLeftArc = !arrivalsOnArc.empty() && arrivalsOnArc.top().time <= departureTime;
        while (vehicleLeftArc) {
            arrivalsOnArc.pop();
            vehicleLeftArc = !arrivalsOnArc.empty() && arrivalsOnArc.top().time <= departureTime;
        }
        return (double) arrivalsOnArc.size() + 1.0;
    }

    auto computeDelayOnArc(const double &vehiclesOnArc,
                           const Instance &instance,
                           const long arc) -> double {
        if (arc == 0) {
            return 0;
        }
        std::vector<double> delays_at_pieces;
        delays_at_pieces.reserve(instance.list_of_slopes.size() + 1); // Reserve space to avoid reallocations

        double height_prev_piece = 0;
        delays_at_pieces.push_back(0); // Initial delay for the first piece

        for (std::size_t i = 0; i < instance.list_of_slopes.size(); ++i) {
            const double th_capacity = instance.list_of_thresholds[i] * instance.nominalCapacitiesArcs[arc];
            const double slope = instance.nominalTravelTimesArcs[arc] * instance.list_of_slopes[i] /
                                 instance.nominalCapacitiesArcs[arc];

            if (vehiclesOnArc > th_capacity) {
                // avoid computing surely not max values
                double delay_current_piece = height_prev_piece + slope * (vehiclesOnArc - th_capacity);
                delays_at_pieces.push_back(delay_current_piece);
            }

            if (i < instance.list_of_slopes.size() - 1) {
                double next_th_cap = instance.list_of_thresholds[i + 1] * instance.nominalCapacitiesArcs[arc];
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
        conflict.currentVehicle = currentVehicleInfo.vehicle;
        conflict.otherVehicle = sortedArrival.vehicle;
        conflict.delayConflict = delay;
        conflict.distanceToCover = sortedArrival.arrival - currentVehicleInfo.departureTime + CONSTR_TOLERANCE;
        conflict.staggeringCurrentVehicle = 0;
        conflict.destaggeringOtherVehicle = 0;
        return conflict;
    }


    auto
    ConflictSearcherNew::getInstructionsConflict(const VehicleSchedule &congestedSchedule,
                                                 long otherPosition) -> InstructionsConflict {
        if (otherVehicleInfo.vehicle == currentVehicleInfo.vehicle) {
            return InstructionsConflict::CONTINUE;
        }
        otherVehicleInfo.earliestDepartureTime = instance.earliestDepartureTimes[otherVehicleInfo.vehicle][otherPosition];
        otherVehicleInfo.earliestArrivalTime = instance.earliestDepartureTimes[otherVehicleInfo.vehicle][otherPosition +
                                                                                                         1];
        otherVehicleInfo.latestDepartureTime = instance.latestDepartureTimes[otherVehicleInfo.vehicle][otherPosition];
        otherVehicleInfo.latestArrivalTime = instance.latestDepartureTimes[otherVehicleInfo.vehicle][otherPosition + 1];

        bool otherComesBeforeAndCannotOverlap =
                otherVehicleInfo.latestArrivalTime <= currentVehicleInfo.earliestDepartureTime;
        bool otherComesBeforeAndCanOverlap =
                otherVehicleInfo.earliestDepartureTime <= currentVehicleInfo.earliestDepartureTime &&
                currentVehicleInfo.earliestDepartureTime <= otherVehicleInfo.latestArrivalTime;
        bool otherComesAfterAndCanOverlap =
                currentVehicleInfo.earliestDepartureTime <= otherVehicleInfo.earliestDepartureTime &&
                otherVehicleInfo.earliestDepartureTime <= currentVehicleInfo.latestDepartureTime;
        bool otherComesAfterAndCannotOverlap =
                otherVehicleInfo.earliestDepartureTime >= currentVehicleInfo.latestDepartureTime;

        if (otherComesBeforeAndCannotOverlap) {
            return InstructionsConflict::CONTINUE;
        } else if (otherComesBeforeAndCanOverlap || otherComesAfterAndCanOverlap) {
            otherVehicleInfo.departureTime = congestedSchedule[otherVehicleInfo.vehicle][otherPosition];
            otherVehicleInfo.arrivalTime = congestedSchedule[otherVehicleInfo.vehicle][otherPosition + 1];
            bool currentConflictsWithOther =
                    otherVehicleInfo.departureTime <= currentVehicleInfo.departureTime &&
                    currentVehicleInfo.departureTime < otherVehicleInfo.arrivalTime;
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
            double conflictDelay = computeDelayOnArc(vehiclesOnArc, instance, arc);
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
        currentVehicleInfo.vehicle = currentVehicle;
        currentVehicleInfo.departureTime = congestedSchedule[currentVehicle][position];
        currentVehicleInfo.arrivalTime = congestedSchedule[currentVehicle][position + 1];
        currentVehicleInfo.earliestDepartureTime = instance.earliestDepartureTimes[currentVehicle][position];
        currentVehicleInfo.latestDepartureTime = instance.latestDepartureTimes[currentVehicle][position];
        currentVehicleInfo.earliestArrivalTime = instance.earliestDepartureTimes[currentVehicle][position + 1];
        currentVehicleInfo.latestArrivalTime = instance.latestDepartureTimes[currentVehicle][position + 1];
    }

    auto
    ConflictSearcherNew::_checkIfVehicleHasDelay(const VehicleSchedule &congestedSchedule,
                                                 long currentVehicle) -> bool {
        const double ffTravelTimeVehicle = instance.freeFlowTravelTimesVehicles[currentVehicle];
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
                    long arc = instance.arcBasedShortestPaths[currentVehicle][position];
                    double delay = congestedSchedule[currentVehicle][position + 1] -
                                   congestedSchedule[currentVehicle][position] -
                                   instance.nominalTravelTimesArcs[arc];
                    if (delay > TOLERANCE) {
                        conflictingArrivals.clear();
                        updateCurrentVehicleInfo(currentVehicle, congestedSchedule, position);
                        for (auto otherVehicle: instance.conflictingSet[arc]) {
                            otherVehicleInfo.vehicle = otherVehicle;
                            const long otherPosition = getIndex(instance.arcBasedShortestPaths[otherVehicle], arc);
                            auto instructionsConflict = getInstructionsConflict(congestedSchedule, otherPosition);
                            if (instructionsConflict == CONTINUE) {
                                continue;
                            } else if (instructionsConflict == BREAK) {
                                break;
                            } else {
                                conflictingArrival.arrival = otherVehicleInfo.arrivalTime;
                                conflictingArrival.vehicle = otherVehicleInfo.vehicle;
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