#include "scheduler.h"
#include <queue>
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::_initializeStatusVehicles() -> void {
        trip_status_list = std::vector<vehicleStatusType>(instance.get_number_of_trips(), vehicleStatusType::INACTIVE);
        number_of_reinsertions = std::vector<long>(instance.get_number_of_trips(), 0);
        last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
    }


    auto
    Scheduler::_initializeSchedulerForUpdatingCongestedSchedule(const VehicleSchedule &congestedSchedule) -> void {
        originalSchedule = congestedSchedule;
        priorityQueueDepartures = MinQueueDepartures();
        departure = Departure();
        otherVehicleDeparture = Departure();
//        greatestTimeAnalyzedOnArcs = std::vector<double>(instance.numberOfArcs, 0);
        tieFound = false;
        lazyUpdatePriorityQueue = false;
        vehicleIsLate = false;
        iteration++;
        printIterationNumber();
    }

    auto
    Scheduler::_addDepartureToPriorityQueue(const double releaseTimeVehicle, const TripID vehicle) -> void {
        departure.trip_id = vehicle;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, 0);
        departure.position = 0;
        last_processed_position[departure.trip_id] = -1;
        departure.time = releaseTimeVehicle;
        departure.eventType = Departure::TRAVEL;
        departure.reinsertionNumber = 0;
        trip_status_list[departure.trip_id] = vehicleStatusType::ACTIVE;
        priorityQueueDepartures.push(departure);


    }

    auto
    Scheduler::_initializePriorityQueue(const Conflict &conflict, Solution &solution) -> void {
        // add vehicles which are staggered at this iteration of the algorithm.
        if (conflict.staggeringCurrentVehicle != 0) {
            _addDepartureToPriorityQueue(solution.get_trip_start_time(conflict.current_trip_id),
                                         conflict.current_trip_id);
            solution.set_trip_arc_departure(conflict.current_trip_id, 0,
                                            solution.get_trip_start_time(conflict.current_trip_id));
        }
        if (conflict.destaggeringOtherVehicle != 0) {
            _addDepartureToPriorityQueue(solution.get_trip_start_time(conflict.other_trip_id),
                                         conflict.other_trip_id);
            solution.set_trip_arc_departure(conflict.other_trip_id, 0,
                                            solution.get_trip_start_time(conflict.other_trip_id));
        }

    }


    auto Scheduler::_checkIfActivationDepartureShouldBeSkipped() -> bool {
        if (trip_status_list[departure.trip_id] == ACTIVE) {
            // trying to activate a vehicle which is active/reinserted -> this event should be skipped
            return true;
        } else if (trip_status_list[departure.trip_id] == STAGING) {
            // this event activates a staging vehicle and becomes a TRAVEL event
            return false;
        } else {
            throw std::invalid_argument("#SKIPDEPARTURE: undefined case");
        }
    }


    auto Scheduler::_checkIfTravelDepartureShouldBeSkipped() -> bool {

        if (departure.position == last_processed_position[departure.trip_id] + 1 &&
            departure.reinsertionNumber == number_of_reinsertions[departure.trip_id]) {
            return false;
        } else {
            printTravelDepartureToSkip();
            return true;
        }
    }

    auto Scheduler::_checkIfDepartureShouldBeSkipped() -> bool {
        if (departure.arc_id == 0) {
            return true; //vehicle at destination
        }
        if (departure.eventType == Departure::ACTIVATION) {
            return _checkIfActivationDepartureShouldBeSkipped();
        } else if (departure.eventType == Departure::TRAVEL) {
            return _checkIfTravelDepartureShouldBeSkipped();
        } else {
            throw std::invalid_argument("departureTime type not existent");
        }
    }

    auto Scheduler::_resetOtherScheduleToReinsertionTime(Solution &solution,
                                                         const long otherVehicle,
                                                         const long otherPosition) -> void {

        long stepsBack = last_processed_position[otherVehicle] - otherPosition;
        for (auto step = 0; step < stepsBack; step++) {
            solution.set_trip_arc_departure(otherVehicle, otherPosition + step + 1,
                                            originalSchedule[otherVehicle][otherPosition +
                                                                           step + 1]);
        }
    }

    auto Scheduler::_reinsertOtherInQueue(Solution &solution,
                                          const long otherVehicle,
                                          const long otherPosition,
                                          const double otherDeparture,
                                          const long arc) -> void {
        _printReinsertionVehicle(arc, otherVehicle, otherDeparture);
        _resetOtherScheduleToReinsertionTime(solution, otherVehicle, otherPosition);
        last_processed_position[otherVehicle] = otherPosition - 1;
        otherVehicleDeparture.trip_id = otherVehicle;
        otherVehicleDeparture.arc_id = arc;
        otherVehicleDeparture.time = otherDeparture;
        otherVehicleDeparture.position = otherPosition;
        otherVehicleDeparture.eventType = Departure::TRAVEL;
        number_of_reinsertions[otherVehicle]++;
        otherVehicleDeparture.reinsertionNumber = number_of_reinsertions[otherVehicle];
        priorityQueueDepartures.push(otherVehicleDeparture);
    }


    auto Scheduler::_check_if_trips_within_conflicting_set_can_conflict(
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
            return InstructionConflictingSet::CONTINUE;
        } else if (other_comes_before_and_overlaps || other_comes_after_and_overlaps) {
            return InstructionConflictingSet::EVALUATE;
        } else if (other_comes_after_and_does_not_overlap) {
            return InstructionConflictingSet::BREAK;
        } else {
            throw std::invalid_argument("Comparing vehicle bounds: undefined case!");
        }
    }


    auto Scheduler::_updateVehiclesOnArcOfConflictingSet(Solution &solution,
                                                         double &vehiclesOnArc) -> void {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (other_trip_id == departure.trip_id) {
                continue;
            }
            const long otherPosition = getIndex(instance.get_trip_route(other_trip_id), departure.arc_id);
            const InstructionConflictingSet instruction = _check_if_trips_within_conflicting_set_can_conflict(
                    other_trip_id, otherPosition);
            if (instruction == InstructionConflictingSet::CONTINUE) {
                continue;
            } else if (instruction == InstructionConflictingSet::BREAK) {
                break;
            }

            const bool otherVehicleIsActive = trip_status_list[other_trip_id] == ACTIVE;
            const bool otherVehicleIsNotActive = !otherVehicleIsActive;
            const double otherDeparture = solution.get_trip_arc_departure(other_trip_id, otherPosition);
            const double otherArrival = solution.get_trip_arc_departure(other_trip_id, otherPosition + 1);
            const bool currentConflictsWithOther = _checkConflictWithOtherVehicle(other_trip_id,
                                                                                  otherDeparture,
                                                                                  otherArrival);
            if (otherVehicleIsNotActive) {
                if (currentConflictsWithOther) { vehiclesOnArc++; }
                vehicleShouldBeMarked shouldMark = _checkIfOtherShouldBeMarked(other_trip_id,
                                                                               otherPosition,
                                                                               currentConflictsWithOther);
                if (shouldMark == YES) {
                    _markVehicle(other_trip_id, otherDeparture, otherPosition); // O(log n) -> pq.push
                    lazyUpdatePriorityQueue = true; //marked vehicle starting before
                    _assertLazyUpdateIsNecessary(otherDeparture);
                    printLazyUpdatePriorityQueue();
                } else if (shouldMark == MAYBE) {
                    vehiclesToMaybeMark.push_back(other_trip_id);
                }
            } else if (otherVehicleIsActive) {
                bool otherIsProcessedOnThisArc = otherPosition <= last_processed_position[other_trip_id];
                const bool otherIsFirst = _checkIfOtherIsFirstInCurrentSchedule(other_trip_id, otherDeparture);
                const bool otherIsNotFirst = !otherIsFirst;
                if (otherIsProcessedOnThisArc) {
                    if (otherIsNotFirst) {
                        _reinsertOtherInQueue(solution, other_trip_id, otherPosition, otherDeparture,
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

    auto Scheduler::_decideOnVehiclesMaybeToMark(const VehicleSchedule &congestedSchedule,
                                                 const double currentNewArrival) -> void {
        for (long other_trip_id: vehiclesToMaybeMark) {
            auto shouldMark = _checkIfShouldMarkGivenCurrentArrivalTime(
                    other_trip_id, currentNewArrival);  // O(1)
            if (shouldMark) {
                const long otherPosition = getIndex(instance.get_trip_route(other_trip_id), departure.arc_id);
                const double otherDeparture = congestedSchedule[other_trip_id][otherPosition];
                _markVehicle(other_trip_id, otherDeparture, otherPosition);
                _assertNoVehiclesDepartingBeforeAreMarked(other_trip_id, congestedSchedule);
            }
        }
    }

    auto Scheduler::_updateTotalValueSolution(Solution &completeSolution) -> void {

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (trip_status_list[trip_id] != ACTIVE) { continue; }

            const double oldDelayVehicle = originalSchedule[trip_id].back() -
                                           originalSchedule[trip_id][0] -
                                           instance.get_trip_free_flow_time(trip_id);
            const double newDelayVehicle = completeSolution.get_trip_schedule(trip_id).back() -
                                           completeSolution.get_trip_start_time(trip_id) -
                                           instance.get_trip_free_flow_time(trip_id);
            completeSolution.increase_total_delay(newDelayVehicle - oldDelayVehicle);
        }
    }


    auto Scheduler::_checkIfTieInSet(const VehicleSchedule &congestedSchedule) -> bool {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (departure.trip_id != other_trip_id) {
                const long otherPosition = getIndex(instance.get_trip_route(other_trip_id), departure.arc_id);
                const InstructionConflictingSet instruction = _check_if_trips_within_conflicting_set_can_conflict(
                        other_trip_id, otherPosition);
                if (instruction == InstructionConflictingSet::CONTINUE) {
                    continue;
                } else if (instruction == InstructionConflictingSet::BREAK) {
                    break;
                }
                Tie tie = {departure.trip_id,
                           other_trip_id,
                           departure.position,
                           otherPosition,
                           departure.arc_id};
                bool tieOnArc = checkIfVehiclesHaveTie(congestedSchedule, tie);
                if (tieOnArc) {
                    return true;
                }
            }
        }
        return false;
    }

    auto Scheduler::_checkIfVehicleIsLate(const double currentVehicleNewArrival) const -> bool {
        if (currentVehicleNewArrival >
            instance.get_trip_arc_latest_departure_time(departure.trip_id, departure.position + 1)) {
            return true;
        }
        return false;
    }

    auto Scheduler::_processConflictingSet(Solution &completeSolution,
                                           double &delay,
                                           double &currentVehicleNewArrival,
                                           double &vehiclesOnArc) -> void {
        _updateVehiclesOnArcOfConflictingSet(completeSolution, vehiclesOnArc);
        if (lazyUpdatePriorityQueue) { return; }
        tieFound = _checkIfTieInSet(completeSolution.get_schedule());
        if (tieFound) {
            return;
        }
        delay = computeDelayOnArc(vehiclesOnArc, instance, departure.arc_id);
        printDelayComputed(delay);
        currentVehicleNewArrival = departure.time + delay + instance.get_arc_travel_time(departure.arc_id);
        vehicleIsLate = _checkIfVehicleIsLate(currentVehicleNewArrival);
        if (vehicleIsLate) {
            return;
        }
        _decideOnVehiclesMaybeToMark(completeSolution.get_schedule(), currentVehicleNewArrival);

    }

    bool isConfSetEmpty(const std::vector<long> &confSet) {
        return confSet.empty();
    }

    auto Scheduler::_processVehicle(Solution &completeSolution) -> void {
        double currentVehicleNewArrival = departure.time + instance.get_arc_travel_time(departure.arc_id);
        double vehiclesOnArc = 1;
        double delay = 0;
        const bool confSetIsEmpty = isConfSetEmpty(instance.get_conflicting_set(departure.arc_id));
        if (!confSetIsEmpty) {
            _processConflictingSet(completeSolution, delay, currentVehicleNewArrival, vehiclesOnArc);
            if (lazyUpdatePriorityQueue || tieFound || vehicleIsLate) {
                return;
            }
        }
        _assertVehiclesOnArcIsCorrect(vehiclesOnArc, completeSolution.get_schedule());
        _updateVehicleSchedule(completeSolution, currentVehicleNewArrival);
        _assertEventPushedToQueueIsCorrect();
        moveVehicleForwardInTheQueue(currentVehicleNewArrival); // O(2 * log n) - pq.push
    }


    auto Scheduler::_activateStagingVehicle() -> void {
        if (departure.eventType == Departure::ACTIVATION) {
            if (trip_status_list[departure.trip_id] == vehicleStatusType::STAGING) {
                departure.eventType = Departure::TRAVEL;
                trip_status_list[departure.trip_id] = vehicleStatusType::ACTIVE;
                last_processed_position[departure.trip_id] = departure.position - 1;
            } else if (trip_status_list[departure.trip_id] == vehicleStatusType::INACTIVE) {
                throw std::invalid_argument("#UPDATEDEPARTURE: activating an INACTIVE vehicle");
            }
        }
    }

    auto Scheduler::_checkIfOtherIsFirstInOriginalSchedule(const long otherVehicle,
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


    auto Scheduler::_checkIfOtherIsFirstInCurrentSchedule(const long otherVehicle,
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


    auto _checkTypeOfMark(const bool otherAlwaysFirst,
                          const bool switchOtherWithCurrentOrder,
                          const bool switchCurrentWithOtherOrder,
                          const bool currentAlwaysFirst,
                          const bool currentConflictsWithOther,
                          const bool otherOverlappedWithCurrent) -> Scheduler::vehicleShouldBeMarked {
        if (otherAlwaysFirst) {
            return Scheduler::NO;
        } else if (switchOtherWithCurrentOrder) {
            if (!otherOverlappedWithCurrent && !currentConflictsWithOther) {
                return Scheduler::NO;
            } else {
                return Scheduler::YES;
            }
        } else if (switchCurrentWithOtherOrder || currentAlwaysFirst) {
            return Scheduler::MAYBE;
        } else {
            throw std::invalid_argument("Check if other should be marked: undefined case");
        }
    }


    auto Scheduler::_checkIfOtherShouldBeMarked(const long otherVehicle,
                                                const long otherPosition,
                                                const bool currentConflictsWithOther) -> vehicleShouldBeMarked {
        _assertOtherIsNotActive(otherVehicle);
        // read info of other vehicle in original schedule (makes sense: it's not marked)
        auto otherOriginalDeparture = originalSchedule[otherVehicle][otherPosition];
        auto currentOriginalDeparture = originalSchedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = originalSchedule[departure.trip_id][departure.position + 1];
        auto otherWasOriginallyFirst = _checkIfOtherIsFirstInOriginalSchedule(otherVehicle,
                                                                              otherOriginalDeparture,
                                                                              currentOriginalDeparture);
        auto otherOverlappedWithCurrent = _checkIfOtherOverlappedWithCurrent(otherVehicle, otherOriginalDeparture,
                                                                             currentOriginalDeparture,
                                                                             currentOriginalArrival);
        bool otherIsFirstNow = _checkIfOtherIsFirstInCurrentSchedule(otherVehicle, otherOriginalDeparture);
        bool currentWasOriginallyFirst = !otherWasOriginallyFirst;
        bool currentIsFirstNow = !otherIsFirstNow;
        // so far we can be sure to not mark the other conflict only if before and after the change was coming before
        bool otherAlwaysFirst = otherWasOriginallyFirst && otherIsFirstNow;
        bool switchOtherWithCurrentOrder = currentWasOriginallyFirst && otherIsFirstNow;
        bool switchCurrentWithOtherOrder = otherWasOriginallyFirst && currentIsFirstNow;
        bool currentAlwaysFirst = currentWasOriginallyFirst && currentIsFirstNow;
        return _checkTypeOfMark(otherAlwaysFirst, switchOtherWithCurrentOrder,
                                switchCurrentWithOtherOrder, currentAlwaysFirst,
                                currentConflictsWithOther, otherOverlappedWithCurrent);
    }

    auto Scheduler::_checkConflictWithOtherVehicle(const long otherVehicle,
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

    auto Scheduler::_checkIfCurrentOverlappedWithOther(const long otherVehicle,
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

    auto Scheduler::_checkIfOtherOverlappedWithCurrent(const long otherVehicle,
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

    auto Scheduler::_checkIfOtherOverlapsNowWithCurrent(const long otherVehicle,
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

    auto Scheduler::_checkConditionsToMark(const bool switchCurrentWithOtherOrder,
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


    auto Scheduler::_checkIfShouldMarkGivenCurrentArrivalTime(const TripID other_trip_id,
                                                              const double currentVehicleNewArrival) -> bool {
        _assertOtherIsNotActive(other_trip_id);
        auto otherPosition = getIndex(instance.get_trip_route(other_trip_id),
                                      departure.arc_id);
        auto otherOriginalDeparture = originalSchedule[other_trip_id][otherPosition];
        auto otherOriginalArrival = originalSchedule[other_trip_id][otherPosition + 1];
        auto currentOriginalDeparture = originalSchedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = originalSchedule[departure.trip_id][departure.position + 1];

        auto currentOverlappedWithOther = _checkIfCurrentOverlappedWithOther(other_trip_id,
                                                                             otherOriginalDeparture,
                                                                             currentOriginalDeparture,
                                                                             otherOriginalArrival);
        auto otherOverlappedWithCurrent = _checkIfOtherOverlappedWithCurrent(other_trip_id, otherOriginalDeparture,
                                                                             currentOriginalDeparture,
                                                                             currentOriginalArrival);

        auto otherOverlapsNowWithCurrent = _checkIfOtherOverlapsNowWithCurrent(other_trip_id,
                                                                               otherOriginalDeparture,
                                                                               currentVehicleNewArrival);

        bool otherIsOriginallyFirst = _checkIfOtherIsFirstInOriginalSchedule(other_trip_id,
                                                                             otherOriginalDeparture,
                                                                             currentOriginalDeparture);

        bool otherIsFirstNow = _checkIfOtherIsFirstInCurrentSchedule(other_trip_id, otherOriginalDeparture);

        bool currentDidNotOverlapWithOther = !currentOverlappedWithOther;
        bool otherDoesNotOverlapWithCurrent = !otherOverlapsNowWithCurrent;
        bool currentIsOriginallyFirst = !otherIsOriginallyFirst;
        bool currentStartsFirstNow = !otherIsFirstNow;

        bool switchCurrentWithOtherOrder = otherIsOriginallyFirst && currentStartsFirstNow;
        bool vehiclesNeverOverlapped = currentDidNotOverlapWithOther && otherDoesNotOverlapWithCurrent;
        bool currentAlwaysFirst = currentIsOriginallyFirst && currentStartsFirstNow;
        bool otherAlwaysOverlaps = otherOverlappedWithCurrent && otherOverlapsNowWithCurrent;
        return _checkConditionsToMark(switchCurrentWithOtherOrder, vehiclesNeverOverlapped,
                                      currentAlwaysFirst, otherAlwaysOverlaps);
    }

    auto
    Scheduler::_markVehicle(const long otherVehicle,
                            const double otherDeparture,
                            const long otherPosition) -> void {
        _assertOtherIsNotActive(otherVehicle);
        otherVehicleDeparture.trip_id = otherVehicle;
        otherVehicleDeparture.arc_id = departure.arc_id;
        otherVehicleDeparture.time = otherDeparture;
        otherVehicleDeparture.position = otherPosition;
        otherVehicleDeparture.reinsertionNumber = 0;
        otherVehicleDeparture.eventType = Departure::ACTIVATION;
        trip_status_list[otherVehicle] = vehicleStatusType::STAGING;
        priorityQueueDepartures.push(otherVehicleDeparture);
    }


    auto Scheduler::moveVehicleForwardInTheQueue(const double currentVehicleNewArrival) -> void {
        _printUpdateGreatestTimeAnalyzed();
        departure.time = currentVehicleNewArrival;
        last_processed_position[departure.trip_id] = departure.position;
        departure.position++;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, departure.position);
        priorityQueueDepartures.push(departure);
        _printDeparturePushedToQueue();
    }


    auto Scheduler::_updateVehicleSchedule(Solution &solution,
                                           const double currentNewArrival) const -> void {
        // update departureTime and arrival in new schedule
        solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        solution.set_trip_arc_departure(departure.trip_id, departure.position + 1, currentNewArrival);
    }


    auto Scheduler::updateExistingCongestedSchedule(Solution &completeSolution,
                                                    const Conflict &conflict) -> void {

        _initializeSchedulerForUpdatingCongestedSchedule(completeSolution.get_schedule());
        _initializeStatusVehicles();
        _initializePriorityQueue(conflict, completeSolution);
        while (!priorityQueueDepartures.empty()) {
            departure = priorityQueueDepartures.top();
            priorityQueueDepartures.pop();
            const auto skipDeparture = _checkIfDepartureShouldBeSkipped();
            if (skipDeparture) { continue; }
            _printDeparture();
            _activateStagingVehicle();
            completeSolution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
            vehiclesToMaybeMark.clear();
            lazyUpdatePriorityQueue = false;
            _processVehicle(completeSolution);
            if (tieFound || vehicleIsLate) {
                completeSolution.set_feasible_and_improving_flag(false);
                return;
            }
            if (lazyUpdatePriorityQueue) {
                priorityQueueDepartures.push(departure);
                continue;
            }
        }
        _updateTotalValueSolution(completeSolution);
        if (completeSolution.get_total_delay() >= best_total_delay) {
            worseSolutions++;
            completeSolution.set_feasible_and_improving_flag(false);
        }
        _assertNoVehiclesAreLate(completeSolution);
    }
}
