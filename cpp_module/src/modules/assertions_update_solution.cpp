#include "stdexcept"
#include <algorithm>
#include <iostream>
#include "scheduler.h"
#include <queue>


namespace cpp_module {

    auto Scheduler::assert_other_starts_after_if_has_to_be_processed_on_this_arc_next(const long otherVehicle,
                                                                                      const long otherPosition,
                                                                                      const double otherDeparture) -> void {
#ifdef assertionsOnEvaluationFunction
        if (lastProcessedPosition[otherVehicle] == otherPosition - 1 & lastProcessedPosition[otherVehicle] != -1) {
        auto otherLastPositionProcessed = lastProcessedPosition[otherVehicle];
        auto otherLastArc = instance.arcBasedShortestPaths[otherVehicle][lastProcessedPosition[otherVehicle]];
        bool otherIsBefore = _checkIfOtherIsFirstInCurrentSchedule(otherVehicle, otherDeparture);
        if (otherIsBefore) {
            std::cout << "Current arc: " << departure.arc << " departureTime time: " << departure.time
                      << " current vehicle reinsertions: " << numberOfReInsertions[departure.vehicle] << "\n";
            std::cout << " Other vehicle: " << otherVehicle << " other position: "
                      << otherPosition << " other departureTime: " << otherDeparture
                      << " other last position processed "
                      << otherLastPositionProcessed << " other last arc " << otherLastArc
                      << " other vehicle reinsertions: "
                      << numberOfReInsertions[otherVehicle] << "\n";
            throw std::invalid_argument("not counting conflict with a vehicle coming before");
        }
    }
#endif
    }


    auto Scheduler::print_delay_computed(const double delay) const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
        std::cout << "delay computed is : " << delay << " \n";
    }
#endif
    }

    auto Scheduler::print_departure() const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout << " Popped departureTime of vehicle " << departure.vehicle << " on arc " << departure.arc
                      << " at time " << departure.time << "postion: " << departure.position << "\n";

        }
#endif
    }

    auto Scheduler::print_iteration_number() const -> void {
#ifdef printsEvaluationFunction
        std::cout << "+++++ CALL EVALUATION FUNCTION: ITERATION " << iteration << "+++++++ \n";
#endif
    }

    auto Scheduler::print_travel_departure_to_skip() -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout
                    << " #SKIPTRAVEL - "
                    << "departureTime.position = " << departure.position
                    << " lastProcessedPosition[departureTime.vehicle] = " << lastProcessedPosition[departure.vehicle]
                    << " departureTime.reinsertionNumber = " << departure.reinsertionNumber
                    << " numberOfReInsertions[departureTime.vehicle] = " << numberOfReInsertions[departure.vehicle]
                    << "\n";
        }
#endif
    }


    auto Scheduler::print_departure_pushed_to_queue() const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout << " Pushing forward departureTime of vehicle " << departure.vehicle << " on arc "
                      << departure.arc <<
                      " at time " << departure.time << "\n";
        }
#endif
    }


    auto
    Scheduler::print_reinsertion_vehicle(const long &arc, const long &vehicle,
                                         const double &departureTime) const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout << "#REINSERTION: vehicle " << vehicle << " on arc " << arc << " time: " << departureTime << "\n";
        }
#endif
    }

    auto Scheduler::assert_analyzing_smallest_departure(VehicleSchedule &congestedSchedule) -> void {
#ifdef assertionsOnEvaluationFunction
        auto minActiveDeparture = std::numeric_limits<double>::max();
        long vehicleToPull;
        for (auto vehicle = 0; vehicle < instance.numberOfVehicles; vehicle++) {
            if (vehicleStatus[vehicle] == ACTIVE) {
                auto lastPositionAnalyzed = lastProcessedPosition[vehicle];
                if (lastPositionAnalyzed ==
                    instance.arcBasedShortestPaths[vehicle].size() - 2) { continue; } //vehicle arrived
                auto departureToAnalyze = congestedSchedule[vehicle][lastPositionAnalyzed + 1];
                if (departureToAnalyze < minActiveDeparture) {
                    minActiveDeparture = departureToAnalyze;
                    vehicleToPull = (long) vehicle;
                }
            }
        }
        if (departure.vehicle == vehicleToPull) { return; }
        if (minActiveDeparture != departure.time) {
            std::cout
                    << "Current departureTime: " << departure.time
                    << " Current vehicle: " << departure.vehicle
                    << " Current arc: " << departure.arc
                    << " Current reinsertions: " << numberOfReInsertions[departure.vehicle] << "\n"
                    << " last processed position current: " << lastProcessedPosition[departure.vehicle]
                    << " min departureTime which should be analyzed: " << minActiveDeparture
                    << " vehicle to analyze: " << vehicleToPull
                    << " last processed position vehicle to analyze: " << lastProcessedPosition[vehicleToPull]
                    << " arc: " << instance.arcBasedShortestPaths[vehicleToPull][lastProcessedPosition[vehicleToPull]]
                    << " reinsertions: " << numberOfReInsertions[vehicleToPull]
                    << "\n";
            throw std::invalid_argument("Not analyzing the smallest departureTime");
        }
#endif
    }

//    auto Scheduler::assert_combination_status_and_departure_type_is_possible() -> void {
//        if (departure.event_type == Departure::ACTIVATION) {
//            if (trip_status_list[departure.trip_id] == Scheduler::TripStatus::INACTIVE) {
//                // only staging vehicles can be activated
//                throw std::invalid_argument("Type of Departure Error: activating an inactive vehicle");
//            } else if (trip_status_list[departure.trip_id] == Scheduler::TripStatus::ACTIVE) {
//                throw std::invalid_argument("Type of Departure Error: activating an active/reinserted vehicle");
//            } else {
//                throw std::invalid_argument("Staging vehicle not correctly activated");
//            }
//
//        } else if (departure.event_type == Departure::TRAVEL) {
//            if (trip_status_list[departure.trip_id] == Scheduler::TripStatus::STAGING) {
//                // wrong
//                throw std::invalid_argument("Type of Departure Error: a staging vehicle is traveling");
//
//            } else if (trip_status_list[departure.trip_id] == Scheduler::TripStatus::INACTIVE) {
//                // wrong
//                throw std::invalid_argument("Type of Departure Error: an inactive vehicle is traveling");
//            }
//            if (departure.reinsertion_number != number_of_reinsertions[departure.trip_id]) {
////                throw std::invalid_argument("Processing wrong travel event of reinserted vehicle");
//            }
//
//        }
//    }

    auto Scheduler::assert_departure_is_feasible(const VehicleSchedule &congestedSchedule) -> void {
#ifdef assertionsOnEvaluationFunction
        if (departure.reinsertionNumber > numberOfReInsertions[departure.vehicle]) {
            throw std::invalid_argument("Departure reinsertion number > number of reinsertions vehicle");
        }

        if (lastProcessedPosition[departure.vehicle] != departure.position - 1) {
            std::cout << "Last processed arc vehicle: " << lastProcessedPosition[departure.vehicle]
                      << "\n ";
            std::cout << "position analyzed: " << departure.position << "\n ";
            throw std::invalid_argument("Last processed position of vehicle is not previous position");
        }

        auto positionToProcess = lastProcessedPosition[departure.vehicle] + 1;
        if (congestedSchedule[departure.vehicle][positionToProcess] != departure.time) {
            std::cout << "Departure time: " << departure.time << "departureTime in schedule: "
                      << congestedSchedule[departure.vehicle][departure.position]
                      << " departureTime in schedule to process "
                      << congestedSchedule[departure.vehicle][positionToProcess] << " number of reinsertions: "
                      << numberOfReInsertions[departure.vehicle] << "\n";

            throw std::invalid_argument("Departure time is different from one in schedule");
        }
        _assertCombinationStatusAndDepartureTypeIsPossible();

#endif
    }

    auto Scheduler::assert_no_vehicles_are_late(Solution &completeSolution) -> void {
#ifdef assertionsOnEvaluationFunction
        for (auto vehicle = 0; vehicle < instance.numberOfVehicles; ++vehicle) {
            if (completeSolution.congestedSchedule[vehicle].back() > instance.deadlines[vehicle] + TOLERANCE) {
                std::cout << "Vehicle " << vehicle << " arrival: " << std::setprecision(25)
                          << completeSolution.congestedSchedule[vehicle].back()
                          << std::setprecision(25) << " deadline: " << instance.deadlines[vehicle] << "\n";
                throw std::invalid_argument("Vehicle is late!");
            }
        }
#endif
    }

    auto Scheduler::check_if_other_starts_before_current(const TripID other_trip_id,
                                                         const VehicleSchedule &congestedSchedule) const -> bool {
        auto indexArcInPathOtherVehicle = get_index(instance.get_trip_route(other_trip_id),
                                                    departure.arc_id);
        auto otherVehicleOriginalDeparture = congestedSchedule[other_trip_id][indexArcInPathOtherVehicle];
        bool otherVehicleComesFirstAfterTheChange =
                otherVehicleOriginalDeparture <= departure.time;
        if (departure.time == otherVehicleOriginalDeparture) {
            if (departure.trip_id < other_trip_id) {
                // current vehicle would pass first - break tie
                otherVehicleComesFirstAfterTheChange = false;
            }
        }
        return otherVehicleComesFirstAfterTheChange;
    }


    auto
    Scheduler::assert_vehicles_on_arc_is_correct(const double vehiclesOnArc,
                                                 const VehicleSchedule &congestedSchedule) -> void {
#ifdef assertionsOnEvaluationFunction
        double testVehiclesOnArc = 1;
        for (auto otherVehicle: instance.conflictingSet[departure.arc]) {
            if (otherVehicle == departure.vehicle) { continue; }
            auto position = getIndex(instance.arcBasedShortestPaths[otherVehicle], departure.arc);
            if (vehicleStatus[otherVehicle] == ACTIVE) {
                bool otherAlreadyProcessedOnThisArc = position <= lastProcessedPosition[otherVehicle];
                bool otherNotProcessedOnThisArc = !otherAlreadyProcessedOnThisArc;
                if (otherNotProcessedOnThisArc) {
                    continue;
                }
            }
            auto departureVehicle = congestedSchedule[otherVehicle][position];
            auto arrivalVehicle = congestedSchedule[otherVehicle][position + 1];
            auto conflict = _checkConflictWithOtherVehicle(otherVehicle, departureVehicle, arrivalVehicle);
            if (conflict) {
                testVehiclesOnArc++;
            }
        }
        if (testVehiclesOnArc != vehiclesOnArc) {
            std::cout << "Legend: INACTIVE: " << vehicleStatusType::INACTIVE <<
                      " STAGING: " << vehicleStatusType::STAGING << " ACTIVE: " << vehicleStatusType::ACTIVE << "\n";
            std::cout << "Current departureTime: " << std::setprecision(10) << departure.time << " vehicle : "
                      << departure.vehicle << " current arc: " << departure.arc << "\n ";
            for (auto otherVehicle: instance.conflictingSet[departure.arc]) {
                if (otherVehicle == departure.vehicle) { continue; }
                auto position = getIndex(instance.arcBasedShortestPaths[otherVehicle], departure.arc);
                auto departureVehicle = congestedSchedule[otherVehicle][position];
                auto arrivalVehicle = congestedSchedule[otherVehicle][position + 1];
                std::cout << "Other vehicle: " << otherVehicle << " other departureTime: "
                          << std::setprecision(10) << departureVehicle
                          << " other arrival: " << std::setprecision(10) << arrivalVehicle << " status other vehicle: "
                          << vehicleStatus[otherVehicle] << " other position: " << position
                          << " other last position processed: " << lastProcessedPosition[otherVehicle] << "\n";

            }
            std::cout << "vehiclesOnArc: " << vehiclesOnArc << " testVehiclesOnArc: " << testVehiclesOnArc << "\n";
            throw std::invalid_argument("Miscounted number of vehicles on arc.");
        }
#endif
    }

    auto Scheduler::assert_no_vehicles_departing_before_are_marked(const long otherVehicle,
                                                                   const VehicleSchedule &congestedSchedule) -> void {
#ifdef assertionsOnEvaluationFunction
        auto markedVehicleWithSmallerDepartureAfterPopping = _checkIfOtherStartsBeforeCurrent(
                otherVehicle, congestedSchedule);
        auto indexArcInPathOtherVehicle = cppModule::getIndex(instance.arcBasedShortestPaths[otherVehicle],
                                                              departure.arc);
        auto otherVehicleOriginalDeparture = congestedSchedule[otherVehicle][indexArcInPathOtherVehicle];
        if (markedVehicleWithSmallerDepartureAfterPopping) {
            std::cout << " Departure current vehicle: " << departure.time
                      << " Departure other vehicle:  " << otherVehicleOriginalDeparture << "\n";
            throw std::invalid_argument("markedVehicleWithSmallerDepartureAfterPopping");
        }
#endif
    }

    auto Scheduler::assert_other_is_not_active(const long otherVehicle) -> void {
#ifdef assertionsOnEvaluationFunction
        if (vehicleStatus[otherVehicle] == vehicleStatusType::ACTIVE) {
            throw std::invalid_argument("Error when checking if vehicle should be staged: staging an active vehicle");
        }
#endif
    }


    auto Scheduler::assert_lazy_update_is_necessary(const double otherDeparture) const -> void {
#ifdef assertionsOnEvaluationFunction
        if (otherDeparture > departure.time) {
            throw std::invalid_argument("Lazy update is not necessary");
        }
#endif
    }


    auto Scheduler::assert_event_pushed_to_queue_is_correct() -> void {
#ifdef assertionsOnEvaluationFunction
        if (departure.eventType != Departure::TRAVEL) {
            if (departure.eventType == Departure::ACTIVATION) {
                throw std::invalid_argument("Error: pushing forward an ACTIVATION  event");
            } else if (departure.reinsertionNumber != numberOfReInsertions[departure.vehicle]) {
                throw std::invalid_argument(
                        "Error: departureTime reinsertion number != number of reinsertions vehicle");
            }

        }
        if (vehicleStatus[departure.vehicle] != ACTIVE) {
            if (vehicleStatus[departure.vehicle] == STAGING) {
                throw std::invalid_argument("Error: pushing forward a STAGING vehicle");
            } else if (vehicleStatus[departure.vehicle] == INACTIVE) {
                throw std::invalid_argument("Error: pushing forward an INACTIVE vehicle");
            } else if (departure.reinsertionNumber != numberOfReInsertions[departure.vehicle]) {
                throw std::invalid_argument(
                        "Error: departureTime reinsertion number != number of reinsertions vehicle");
            }
        }
#endif
    }

    auto Scheduler::print_lazy_update_priority_queue() const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout << "lazy update priority queue #1\n";
        }
#endif
    }


    auto Scheduler::print_update_greatest_time_analyzed() const -> void {
#ifdef printsEvaluationFunction
        if (iteration == ITERATION_TO_PRINT) {
            std::cout << "updating greatest time analyzed ON ARC" << departure.arc << ":"
                      << departure.time << " vehicle considered :" << departure.vehicle << "\n";
        }
#endif
    }

}