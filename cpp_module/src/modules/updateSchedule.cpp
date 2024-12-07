#include "module.h"
#include <queue>
#include <utility>
#include "algorithm"
#include "iostream"
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::_initializeStatusVehicles() -> void {
        vehicleStatus = std::vector<vehicleStatusType>(instance.numberOfVehicles, vehicleStatusType::INACTIVE);
        numberOfReInsertions = std::vector<long>(instance.numberOfVehicles, 0);
        lastProcessedPosition = std::vector<long>(instance.numberOfVehicles, -1);
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
    Scheduler::_addDepartureToPriorityQueue(const double releaseTimeVehicle, const long vehicle) -> void {
        departure.vehicle = vehicle;
        departure.arc = instance.arcBasedShortestPaths[departure.vehicle][0];
        departure.position = 0;
        lastProcessedPosition[departure.vehicle] = -1;
        departure.time = releaseTimeVehicle;
        departure.eventType = Departure::TRAVEL;
        departure.reinsertionNumber = 0;
        vehicleStatus[departure.vehicle] = vehicleStatusType::ACTIVE;
        priorityQueueDepartures.push(departure);


    }

    auto
    Scheduler::_initializePriorityQueue(const Conflict &conflict, Solution &completeSolution) -> void {
        // add vehicles which are staggered at this iteration of the algorithm.
        if (conflict.staggeringCurrentVehicle != 0) {
            _addDepartureToPriorityQueue(completeSolution.releaseTimes[conflict.currentVehicle],
                                         conflict.currentVehicle);
            completeSolution.schedule[conflict.currentVehicle][0] = completeSolution.releaseTimes[conflict.currentVehicle];
        }
        if (conflict.destaggeringOtherVehicle != 0) {
            _addDepartureToPriorityQueue(completeSolution.releaseTimes[conflict.otherVehicle],
                                         conflict.otherVehicle);
            completeSolution.schedule[conflict.otherVehicle][0] = completeSolution.releaseTimes[conflict.otherVehicle];
        }

    }


    auto Scheduler::_checkIfActivationDepartureShouldBeSkipped() -> bool {
        if (vehicleStatus[departure.vehicle] == ACTIVE) {
            // trying to activate a vehicle which is active/reinserted -> this event should be skipped
            return true;
        } else if (vehicleStatus[departure.vehicle] == STAGING) {
            // this event activates a staging vehicle and becomes a TRAVEL event
            return false;
        } else {
            throw std::invalid_argument("#SKIPDEPARTURE: undefined case");
        }
    }


    auto Scheduler::_checkIfTravelDepartureShouldBeSkipped() -> bool {

        if (departure.position == lastProcessedPosition[departure.vehicle] + 1 &&
            departure.reinsertionNumber == numberOfReInsertions[departure.vehicle]) {
            return false;
        } else {
            printTravelDepartureToSkip();
            return true;
        }
    }

    auto Scheduler::_checkIfDepartureShouldBeSkipped() -> bool {
        if (departure.arc == 0) {
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

    auto Scheduler::_resetOtherScheduleToReinsertionTime(VehicleSchedule &congestedSchedule,
                                                         const long otherVehicle,
                                                         const long otherPosition) -> void {

        long stepsBack = lastProcessedPosition[otherVehicle] - otherPosition;
        for (auto step = 0; step < stepsBack; step++) {
            congestedSchedule[otherVehicle][otherPosition + step + 1] = originalSchedule[otherVehicle][otherPosition +
                                                                                                       step + 1];
        }
    }

    auto Scheduler::_reinsertOtherInQueue(VehicleSchedule &congestedSchedule,
                                          const long otherVehicle,
                                          const long otherPosition,
                                          const double otherDeparture,
                                          const long arc) -> void {
        _printReinsertionVehicle(arc, otherVehicle, otherDeparture);
        _resetOtherScheduleToReinsertionTime(congestedSchedule, otherVehicle, otherPosition);
        lastProcessedPosition[otherVehicle] = otherPosition - 1;
        otherVehicleDeparture.vehicle = otherVehicle;
        otherVehicleDeparture.arc = arc;
        otherVehicleDeparture.time = otherDeparture;
        otherVehicleDeparture.position = otherPosition;
        otherVehicleDeparture.eventType = Departure::TRAVEL;
        numberOfReInsertions[otherVehicle]++;
        otherVehicleDeparture.reinsertionNumber = numberOfReInsertions[otherVehicle];
        priorityQueueDepartures.push(otherVehicleDeparture);
    }


    auto Scheduler::_checkIfTripsWithinSameConflictingSetCanHaveAConflict(const long otherVehicle,
                                                                          const long otherPosition) -> InstructionConflictingSet {
        //hp: the trips in the conflciting set are ordered by ascending earliest departureTime time
        double currentEarliestDepartureTime = instance.earliestDepartureTimes[departure.vehicle][departure.position];
        double currentLatestArrivalTime = instance.latestDepartureTimes[departure.vehicle][departure.position + 1];

        double otherEarliestDepartureTime = instance.earliestDepartureTimes[otherVehicle][otherPosition];
        double otherLatestArrivalTime = instance.latestDepartureTimes[otherVehicle][otherPosition + 1];

        bool otherComesBeforeAndDoesNotOverlap = otherLatestArrivalTime < currentEarliestDepartureTime;
        bool otherComesBeforeAndOverlaps = otherEarliestDepartureTime <= currentEarliestDepartureTime &&
                                           currentEarliestDepartureTime < otherLatestArrivalTime;
        bool otherComesAfterAndOverlaps = currentEarliestDepartureTime <= otherEarliestDepartureTime &&
                                          otherEarliestDepartureTime < currentLatestArrivalTime;
        bool otherComesAfterAndDoesNotOverlap = otherEarliestDepartureTime > currentLatestArrivalTime;
        // First case: continue -> other vehicle lastest arrival is smaller than current vehicle earliest departureTime
        if (otherComesBeforeAndDoesNotOverlap) {
            return InstructionConflictingSet::CONTINUE;
        } else if (otherComesBeforeAndOverlaps || otherComesAfterAndOverlaps) {
            // Second case: evaluate -> there is an overlap between the two intervals
            return InstructionConflictingSet::EVALUATE;
        } else if (otherComesAfterAndDoesNotOverlap) {
            //Third case: break -> from now on the vehicles you will consider will always meet otherComesAfterAndDoesNotOverlap condition
            return InstructionConflictingSet::BREAK;
        } else {
            throw std::invalid_argument("comparing vehicles bounds: undefined case!");
        }
    }

    auto Scheduler::_updateVehiclesOnArcOfConflictingSet(VehicleSchedule &congestedSchedule,
                                                         double &vehiclesOnArc) -> void {
        for (auto otherVehicle: instance.conflictingSet[departure.arc]) {
            if (otherVehicle == departure.vehicle) {
                continue;
            }
            const long otherPosition = getIndex(instance.arcBasedShortestPaths[otherVehicle], departure.arc);
            const InstructionConflictingSet instruction = _checkIfTripsWithinSameConflictingSetCanHaveAConflict(
                    otherVehicle, otherPosition);
            if (instruction == InstructionConflictingSet::CONTINUE) {
                continue;
            } else if (instruction == InstructionConflictingSet::BREAK) {
                break;
            }

            const bool otherVehicleIsActive = vehicleStatus[otherVehicle] == ACTIVE;
            const bool otherVehicleIsNotActive = !otherVehicleIsActive;
            const double otherDeparture = congestedSchedule[otherVehicle][otherPosition];
            const double otherArrival = congestedSchedule[otherVehicle][otherPosition + 1];
            const bool currentConflictsWithOther = _checkConflictWithOtherVehicle(otherVehicle,
                                                                                  otherDeparture,
                                                                                  otherArrival);
            if (otherVehicleIsNotActive) {
                if (currentConflictsWithOther) { vehiclesOnArc++; }
                vehicleShouldBeMarked shouldMark = _checkIfOtherShouldBeMarked(otherVehicle,
                                                                               otherPosition,
                                                                               currentConflictsWithOther);
                if (shouldMark == YES) {
                    _markVehicle(otherVehicle, otherDeparture, otherPosition); // O(log n) -> pq.push
                    lazyUpdatePriorityQueue = true; //marked vehicle starting before
                    _assertLazyUpdateIsNecessary(otherDeparture);
                    printLazyUpdatePriorityQueue();
                } else if (shouldMark == MAYBE) {
                    vehiclesToMaybeMark.push_back(otherVehicle);
                }
            } else if (otherVehicleIsActive) {
                bool otherIsProcessedOnThisArc = otherPosition <= lastProcessedPosition[otherVehicle];
                const bool otherIsFirst = _checkIfOtherIsFirstInCurrentSchedule(otherVehicle, otherDeparture);
                const bool otherIsNotFirst = !otherIsFirst;
                if (otherIsProcessedOnThisArc) {
                    if (otherIsNotFirst) {
                        _reinsertOtherInQueue(congestedSchedule, otherVehicle, otherPosition, otherDeparture,
                                              departure.arc);
                        continue;
                    }
                    if (currentConflictsWithOther) {
                        vehiclesOnArc++;
                    }
                }
                _assertOtherStartsAfterIfHasToBeProcessedOnThisArcNext(otherVehicle, otherPosition, otherDeparture);
            }
        }
    }

    auto Scheduler::_decideOnVehiclesMaybeToMark(const VehicleSchedule &congestedSchedule,
                                                 const double currentNewArrival) -> void {
        for (long otherVehicle: vehiclesToMaybeMark) {
            auto shouldMark = _checkIfShouldMarkGivenCurrentArrivalTime(
                    otherVehicle, currentNewArrival);  // O(1)
            if (shouldMark) {
                const long otherPosition = getIndex(instance.arcBasedShortestPaths[otherVehicle], departure.arc);
                const double otherDeparture = congestedSchedule[otherVehicle][otherPosition];
                _markVehicle(otherVehicle, otherDeparture, otherPosition);
                _assertNoVehiclesDepartingBeforeAreMarked(otherVehicle, congestedSchedule);
            }
        }
    }

    auto Scheduler::_updateTotalValueSolution(Solution &completeSolution) -> void {

        for (auto vehicle = 0; vehicle < instance.numberOfVehicles; ++vehicle) {
            if (vehicleStatus[vehicle] != ACTIVE) { continue; }

            const double oldDelayVehicle = originalSchedule[vehicle].back() -
                                           originalSchedule[vehicle][0] -
                                           instance.freeFlowTravelTimesVehicles[vehicle];
            const double newDelayVehicle = completeSolution.schedule[vehicle].back() -
                                           completeSolution.releaseTimes[vehicle] -
                                           instance.freeFlowTravelTimesVehicles[vehicle];
            completeSolution.total_delay += (newDelayVehicle - oldDelayVehicle);
            const double OldTardinessVehicle = std::max(0.0,
                                                        originalSchedule[vehicle].back() - instance.dueDates[vehicle]);
            const double newTardinessOnArc = std::max(0.0,
                                                      completeSolution.schedule[vehicle].back() -
                                                      instance.dueDates[vehicle]);
            completeSolution.totalTardiness += (newTardinessOnArc - OldTardinessVehicle);

        }
        assertTotalTardinessIsNotNegative(completeSolution.totalTardiness);
        completeSolution.solutionValue = completeSolution.total_delay;
    }


    auto Scheduler::_checkIfTieInSet(const VehicleSchedule &congestedSchedule) -> bool {
        for (auto otherVehicle: instance.conflictingSet[departure.arc]) {
            if (departure.vehicle != otherVehicle) {
                const long otherPosition = getIndex(instance.arcBasedShortestPaths[otherVehicle], departure.arc);
                const InstructionConflictingSet instruction = _checkIfTripsWithinSameConflictingSetCanHaveAConflict(
                        otherVehicle, otherPosition);
                if (instruction == InstructionConflictingSet::CONTINUE) {
                    continue;
                } else if (instruction == InstructionConflictingSet::BREAK) {
                    break;
                }
                Tie tie = {departure.vehicle,
                           otherVehicle,
                           departure.position,
                           otherPosition,
                           departure.arc};
                bool tieOnArc = checkIfVehiclesHaveTie(congestedSchedule, tie);
                if (tieOnArc) {
                    return true;
                }
            }
        }
        return false;
    }

    auto Scheduler::_checkIfVehicleIsLate(const double currentVehicleNewArrival) -> bool {
        if (currentVehicleNewArrival > instance.latestDepartureTimes[departure.vehicle][departure.position + 1]) {
            return true;
        }
        return false;
    }

    auto Scheduler::_processConflictingSet(Solution &completeSolution,
                                           double &delay,
                                           double &currentVehicleNewArrival,
                                           double &vehiclesOnArc) -> void {
        _updateVehiclesOnArcOfConflictingSet(completeSolution.schedule, vehiclesOnArc);
        if (lazyUpdatePriorityQueue) { return; }
        tieFound = _checkIfTieInSet(completeSolution.schedule);
        if (tieFound) {
            return;
        }
        delay = computeDelayOnArc(vehiclesOnArc, instance, departure.arc);
        printDelayComputed(delay);
        currentVehicleNewArrival = departure.time + delay + instance.nominalTravelTimesArcs[departure.arc];
        vehicleIsLate = _checkIfVehicleIsLate(currentVehicleNewArrival);
        if (vehicleIsLate) {
            return;
        }
        _decideOnVehiclesMaybeToMark(completeSolution.schedule, currentVehicleNewArrival);

    }

    bool isConfSetEmpty(const std::vector<long> &confSet) {
        return confSet.empty();
    }

    auto Scheduler::_processVehicle(Solution &completeSolution) -> void {
        double currentVehicleNewArrival = departure.time + instance.nominalTravelTimesArcs[departure.arc];
        double vehiclesOnArc = 1;
        double delay = 0;
        const bool confSetIsEmpty = isConfSetEmpty(instance.conflictingSet[departure.arc]);
        if (!confSetIsEmpty) {
            _processConflictingSet(completeSolution, delay, currentVehicleNewArrival, vehiclesOnArc);
            if (lazyUpdatePriorityQueue || tieFound || vehicleIsLate) {
                return;
            }
        }
        _assertVehiclesOnArcIsCorrect(vehiclesOnArc, completeSolution.schedule);
        _updateVehicleSchedule(completeSolution.schedule, currentVehicleNewArrival);
        _assertEventPushedToQueueIsCorrect();
        moveVehicleForwardInTheQueue(currentVehicleNewArrival); // O(2 * log n) - pq.push
    }


    auto Scheduler::_activateStagingVehicle() -> void {
        if (departure.eventType == Departure::ACTIVATION) {
            if (vehicleStatus[departure.vehicle] == vehicleStatusType::STAGING) {
                departure.eventType = Departure::TRAVEL;
                vehicleStatus[departure.vehicle] = vehicleStatusType::ACTIVE;
                lastProcessedPosition[departure.vehicle] = departure.position - 1;
            } else if (vehicleStatus[departure.vehicle] == vehicleStatusType::INACTIVE) {
                throw std::invalid_argument("#UPDATEDEPARTURE: activating an INACTIVE vehicle");
            }
        }
    }

    auto Scheduler::_checkIfOtherIsFirstInOriginalSchedule(const long otherVehicle,
                                                           const double otherOriginalDeparture,
                                                           const double currentOriginalDeparture) const -> bool {
        bool otherIsFirstInOriginalSchedule = otherOriginalDeparture <= currentOriginalDeparture;
        if (otherOriginalDeparture == currentOriginalDeparture) {
            if (departure.vehicle < otherVehicle) {
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
            if (departure.vehicle < otherVehicle) {
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
        auto currentOriginalDeparture = originalSchedule[departure.vehicle][departure.position];
        auto currentOriginalArrival = originalSchedule[departure.vehicle][departure.position + 1];
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
            if (departure.vehicle < otherVehicle) {
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
            if (departure.vehicle < otherVehicle) {
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
            if (otherVehicle < departure.vehicle) {
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
            if (otherVehicle < departure.vehicle) {
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


    auto Scheduler::_checkIfShouldMarkGivenCurrentArrivalTime(const long otherVehicle,
                                                              const double currentVehicleNewArrival) -> bool {
        _assertOtherIsNotActive(otherVehicle);
        auto otherPosition = getIndex(instance.arcBasedShortestPaths[otherVehicle],
                                      departure.arc);
        auto otherOriginalDeparture = originalSchedule[otherVehicle][otherPosition];
        auto otherOriginalArrival = originalSchedule[otherVehicle][otherPosition + 1];
        auto currentOriginalDeparture = originalSchedule[departure.vehicle][departure.position];
        auto currentOriginalArrival = originalSchedule[departure.vehicle][departure.position + 1];

        auto currentOverlappedWithOther = _checkIfCurrentOverlappedWithOther(otherVehicle,
                                                                             otherOriginalDeparture,
                                                                             currentOriginalDeparture,
                                                                             otherOriginalArrival);
        auto otherOverlappedWithCurrent = _checkIfOtherOverlappedWithCurrent(otherVehicle, otherOriginalDeparture,
                                                                             currentOriginalDeparture,
                                                                             currentOriginalArrival);

        auto otherOverlapsNowWithCurrent = _checkIfOtherOverlapsNowWithCurrent(otherVehicle,
                                                                               otherOriginalDeparture,
                                                                               currentVehicleNewArrival);

        bool otherIsOriginallyFirst = _checkIfOtherIsFirstInOriginalSchedule(otherVehicle,
                                                                             otherOriginalDeparture,
                                                                             currentOriginalDeparture);

        bool otherIsFirstNow = _checkIfOtherIsFirstInCurrentSchedule(otherVehicle, otherOriginalDeparture);

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
        otherVehicleDeparture.vehicle = otherVehicle;
        otherVehicleDeparture.arc = departure.arc;
        otherVehicleDeparture.time = otherDeparture;
        otherVehicleDeparture.position = otherPosition;
        otherVehicleDeparture.reinsertionNumber = 0;
        otherVehicleDeparture.eventType = Departure::ACTIVATION;
        vehicleStatus[otherVehicle] = vehicleStatusType::STAGING;
        priorityQueueDepartures.push(otherVehicleDeparture);
    }


    auto Scheduler::moveVehicleForwardInTheQueue(const double currentVehicleNewArrival) -> void {
        _printUpdateGreatestTimeAnalyzed();
        departure.time = currentVehicleNewArrival;
        lastProcessedPosition[departure.vehicle] = departure.position;
        departure.position++;
        departure.arc = instance.arcBasedShortestPaths[departure.vehicle][departure.position];
        priorityQueueDepartures.push(departure);
        _printDeparturePushedToQueue();
    }


    auto Scheduler::_updateVehicleSchedule(VehicleSchedule &congestedSchedule,
                                           const double currentNewArrival) const -> void {


        // update departureTime and arrival in new schedule
        congestedSchedule[departure.vehicle][departure.position] = departure.time;
        congestedSchedule[departure.vehicle][departure.position + 1] = currentNewArrival;
    }


    auto Scheduler::updateExistingCongestedSchedule(Solution &completeSolution,
                                                    const Conflict &conflict) -> void {

        _initializeSchedulerForUpdatingCongestedSchedule(completeSolution.schedule);
        _initializeStatusVehicles();
        _initializePriorityQueue(conflict, completeSolution);
        while (!priorityQueueDepartures.empty()) {
            departure = priorityQueueDepartures.top();
            priorityQueueDepartures.pop();
            const auto skipDeparture = _checkIfDepartureShouldBeSkipped();
            if (skipDeparture) { continue; }
            _printDeparture();
            _activateStagingVehicle();
            completeSolution.schedule[departure.vehicle][departure.position] = departure.time;
            _assertDepartureIsFeasible(completeSolution.schedule);
            vehiclesToMaybeMark.clear();
            lazyUpdatePriorityQueue = false;
            _assertAnalyzingSmallestDeparture(completeSolution.schedule);
            _processVehicle(completeSolution);
            if (tieFound || vehicleIsLate) {
                completeSolution.scheduleIsFeasibleAndImproving = false;
                return;
            }
            if (lazyUpdatePriorityQueue) {
                priorityQueueDepartures.push(departure);
                continue;
            }
        }
        _updateTotalValueSolution(completeSolution);
        if (completeSolution.solutionValue >= bestSolutionValue) {
            worseSolutions++;
            completeSolution.scheduleIsFeasibleAndImproving = false;
        }
        if (completeSolution.timesCapIsReached > maxTimesCapReached) {
            completeSolution.scheduleIsFeasibleAndImproving = false;
        }
        _assertNoVehiclesAreLate(completeSolution);
    }
}
