#include "scheduler.h"
#include <queue>
#include "stdexcept"

namespace cpp_module {

    auto Scheduler::initialize_status_vehicles() -> void {
        trip_status_list = std::vector<vehicleStatusType>(instance.get_number_of_trips(), vehicleStatusType::INACTIVE);
        number_of_reinsertions = std::vector<long>(instance.get_number_of_trips(), 0);
        last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
    }


    auto
    Scheduler::initialize_scheduler_for_update_solution(const VehicleSchedule &congestedSchedule) -> void {
        original_schedule = congestedSchedule;
        pq_departures = MinQueueDepartures();
        departure = Departure();
        other_trip_departure = Departure();
//        greatestTimeAnalyzedOnArcs = std::vector<double>(instance.numberOfArcs, 0);
        tie_found = false;
        lazy_update_pq = false;
        trip_is_late = false;
        iteration++;
        printIterationNumber();
    }

    auto
    Scheduler::add_departure_to_priority_queue(const double releaseTimeVehicle, const TripID vehicle) -> void {
        departure.trip_id = vehicle;
        departure.arc_id = instance.get_arc_at_position_in_trip_route(departure.trip_id, 0);
        departure.position = 0;
        last_processed_position[departure.trip_id] = -1;
        departure.time = releaseTimeVehicle;
        departure.eventType = Departure::TRAVEL;
        departure.reinsertionNumber = 0;
        trip_status_list[departure.trip_id] = vehicleStatusType::ACTIVE;
        pq_departures.push(departure);


    }

    auto
    Scheduler::initialize_priority_queue(const Conflict &conflict, Solution &solution) -> void {
        // add vehicles which are staggered at this iteration of the algorithm.
        if (conflict.staggeringCurrentVehicle != 0) {
            add_departure_to_priority_queue(solution.get_trip_start_time(conflict.current_trip_id),
                                            conflict.current_trip_id);
            solution.set_trip_arc_departure(conflict.current_trip_id, 0,
                                            solution.get_trip_start_time(conflict.current_trip_id));
        }
        if (conflict.destaggeringOtherVehicle != 0) {
            add_departure_to_priority_queue(solution.get_trip_start_time(conflict.other_trip_id),
                                            conflict.other_trip_id);
            solution.set_trip_arc_departure(conflict.other_trip_id, 0,
                                            solution.get_trip_start_time(conflict.other_trip_id));
        }

    }


    auto Scheduler::check_if_activation_departure_should_be_skipped() -> bool {
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


    auto Scheduler::check_if_travel_departure_should_be_skipped() -> bool {

        if (departure.position == last_processed_position[departure.trip_id] + 1 &&
            departure.reinsertionNumber == number_of_reinsertions[departure.trip_id]) {
            return false;
        } else {
            printTravelDepartureToSkip();
            return true;
        }
    }

    auto Scheduler::check_if_departure_should_be_skipped() -> bool {
        if (departure.arc_id == 0) {
            return true; //vehicle at destination
        }
        if (departure.eventType == Departure::ACTIVATION) {
            return check_if_activation_departure_should_be_skipped();
        } else if (departure.eventType == Departure::TRAVEL) {
            return check_if_travel_departure_should_be_skipped();
        } else {
            throw std::invalid_argument("departureTime type not existent");
        }
    }

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

    auto Scheduler::reinsert_other_in_queue(Solution &solution,
                                            const long otherVehicle,
                                            const long otherPosition,
                                            const double otherDeparture,
                                            const long arc) -> void {
        _printReinsertionVehicle(arc, otherVehicle, otherDeparture);
        reset_other_schedule_to_reinsertion_time(solution, otherVehicle, otherPosition);
        last_processed_position[otherVehicle] = otherPosition - 1;
        other_trip_departure.trip_id = otherVehicle;
        other_trip_departure.arc_id = arc;
        other_trip_departure.time = otherDeparture;
        other_trip_departure.position = otherPosition;
        other_trip_departure.eventType = Departure::TRAVEL;
        number_of_reinsertions[otherVehicle]++;
        other_trip_departure.reinsertionNumber = number_of_reinsertions[otherVehicle];
        pq_departures.push(other_trip_departure);
    }


    auto Scheduler::check_if_trips_within_conflicting_set_can_conflict(
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


    auto Scheduler::update_vehicles_on_arc_of_conflicting_set(Solution &solution,
                                                              double &vehiclesOnArc) -> void {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (other_trip_id == departure.trip_id) {
                continue;
            }
            const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
            const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
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
            const bool currentConflictsWithOther = check_conflict_with_other_vehicle(other_trip_id,
                                                                                     otherDeparture,
                                                                                     otherArrival);
            if (otherVehicleIsNotActive) {
                if (currentConflictsWithOther) { vehiclesOnArc++; }
                vehicleShouldBeMarked shouldMark = check_if_other_should_be_marked(other_trip_id,
                                                                                   otherPosition,
                                                                                   currentConflictsWithOther);
                if (shouldMark == YES) {
                    mark_vehicle(other_trip_id, otherDeparture, otherPosition); // O(log n) -> pq.push
                    lazy_update_pq = true; //marked vehicle starting before
                    _assertLazyUpdateIsNecessary(otherDeparture);
                    printLazyUpdatePriorityQueue();
                } else if (shouldMark == MAYBE) {
                    vehicles_to_mark.push_back(other_trip_id);
                }
            } else if (otherVehicleIsActive) {
                bool otherIsProcessedOnThisArc = otherPosition <= last_processed_position[other_trip_id];
                const bool otherIsFirst = check_if_other_is_first_in_current_schedule(other_trip_id, otherDeparture);
                const bool otherIsNotFirst = !otherIsFirst;
                if (otherIsProcessedOnThisArc) {
                    if (otherIsNotFirst) {
                        reinsert_other_in_queue(solution, other_trip_id, otherPosition, otherDeparture,
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

    auto Scheduler::decide_on_vehicles_maybe_to_mark(const VehicleSchedule &congestedSchedule,
                                                     const double currentNewArrival) -> void {
        for (long other_trip_id: vehicles_to_mark) {
            auto shouldMark = check_if_should_mark_given_current_arrival_time(
                    other_trip_id, currentNewArrival);  // O(1)
            if (shouldMark) {
                const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const double otherDeparture = congestedSchedule[other_trip_id][otherPosition];
                mark_vehicle(other_trip_id, otherDeparture, otherPosition);
                _assertNoVehiclesDepartingBeforeAreMarked(other_trip_id, congestedSchedule);
            }
        }
    }

    auto Scheduler::update_total_value_solution(Solution &completeSolution) -> void {

        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
            if (trip_status_list[trip_id] != ACTIVE) { continue; }

            const double oldDelayVehicle = original_schedule[trip_id].back() -
                                           original_schedule[trip_id][0] -
                                           instance.get_trip_free_flow_time(trip_id);
            const double newDelayVehicle = completeSolution.get_trip_schedule(trip_id).back() -
                                           completeSolution.get_trip_start_time(trip_id) -
                                           instance.get_trip_free_flow_time(trip_id);
            completeSolution.increase_total_delay(newDelayVehicle - oldDelayVehicle);
        }
    }


    auto Scheduler::check_if_tie_in_set(const VehicleSchedule &congestedSchedule) -> bool {
        for (auto other_trip_id: instance.get_conflicting_set(departure.arc_id)) {
            if (departure.trip_id != other_trip_id) {
                const long otherPosition = get_index(instance.get_trip_route(other_trip_id), departure.arc_id);
                const InstructionConflictingSet instruction = check_if_trips_within_conflicting_set_can_conflict(
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
                bool tieOnArc = check_if_vehicles_have_tie(congestedSchedule, tie);
                if (tieOnArc) {
                    return true;
                }
            }
        }
        return false;
    }

    auto Scheduler::check_if_vehicle_is_late(const double currentVehicleNewArrival) const -> bool {
        if (currentVehicleNewArrival >
            instance.get_trip_arc_latest_departure_time(departure.trip_id, departure.position + 1)) {
            return true;
        }
        return false;
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


    auto Scheduler::activate_staging_vehicle() -> void {
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


    auto check_type_of_mark(const bool otherAlwaysFirst,
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


    auto Scheduler::check_if_other_should_be_marked(const long otherVehicle,
                                                    const long otherPosition,
                                                    const bool currentConflictsWithOther) -> vehicleShouldBeMarked {
        _assertOtherIsNotActive(otherVehicle);
        // read info of other vehicle in original schedule (makes sense: it's not marked)
        auto otherOriginalDeparture = original_schedule[otherVehicle][otherPosition];
        auto currentOriginalDeparture = original_schedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = original_schedule[departure.trip_id][departure.position + 1];
        auto otherWasOriginallyFirst = check_if_other_is_first_in_original_schedule(otherVehicle,
                                                                                    otherOriginalDeparture,
                                                                                    currentOriginalDeparture);
        auto otherOverlappedWithCurrent = check_if_other_overlapped_with_current(otherVehicle, otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 currentOriginalArrival);
        bool otherIsFirstNow = check_if_other_is_first_in_current_schedule(otherVehicle, otherOriginalDeparture);
        bool currentWasOriginallyFirst = !otherWasOriginallyFirst;
        bool currentIsFirstNow = !otherIsFirstNow;
        // so far we can be sure to not mark the other conflict only if before and after the change was coming before
        bool otherAlwaysFirst = otherWasOriginallyFirst && otherIsFirstNow;
        bool switchOtherWithCurrentOrder = currentWasOriginallyFirst && otherIsFirstNow;
        bool switchCurrentWithOtherOrder = otherWasOriginallyFirst && currentIsFirstNow;
        bool currentAlwaysFirst = currentWasOriginallyFirst && currentIsFirstNow;
        return check_type_of_mark(otherAlwaysFirst, switchOtherWithCurrentOrder,
                                  switchCurrentWithOtherOrder, currentAlwaysFirst,
                                  currentConflictsWithOther, otherOverlappedWithCurrent);
    }

    auto Scheduler::check_conflict_with_other_vehicle(const long otherVehicle,
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


    auto Scheduler::check_if_should_mark_given_current_arrival_time(const TripID other_trip_id,
                                                                    const double currentVehicleNewArrival) -> bool {
        _assertOtherIsNotActive(other_trip_id);
        auto otherPosition = get_index(instance.get_trip_route(other_trip_id),
                                       departure.arc_id);
        auto otherOriginalDeparture = original_schedule[other_trip_id][otherPosition];
        auto otherOriginalArrival = original_schedule[other_trip_id][otherPosition + 1];
        auto currentOriginalDeparture = original_schedule[departure.trip_id][departure.position];
        auto currentOriginalArrival = original_schedule[departure.trip_id][departure.position + 1];

        auto currentOverlappedWithOther = check_if_current_overlapped_with_other(other_trip_id,
                                                                                 otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 otherOriginalArrival);
        auto otherOverlappedWithCurrent = check_if_other_overlapped_with_current(other_trip_id, otherOriginalDeparture,
                                                                                 currentOriginalDeparture,
                                                                                 currentOriginalArrival);

        auto otherOverlapsNowWithCurrent = check_if_other_overlaps_now_with_current(other_trip_id,
                                                                                    otherOriginalDeparture,
                                                                                    currentVehicleNewArrival);

        bool otherIsOriginallyFirst = check_if_other_is_first_in_original_schedule(other_trip_id,
                                                                                   otherOriginalDeparture,
                                                                                   currentOriginalDeparture);

        bool otherIsFirstNow = check_if_other_is_first_in_current_schedule(other_trip_id, otherOriginalDeparture);

        bool currentDidNotOverlapWithOther = !currentOverlappedWithOther;
        bool otherDoesNotOverlapWithCurrent = !otherOverlapsNowWithCurrent;
        bool currentIsOriginallyFirst = !otherIsOriginallyFirst;
        bool currentStartsFirstNow = !otherIsFirstNow;

        bool switchCurrentWithOtherOrder = otherIsOriginallyFirst && currentStartsFirstNow;
        bool vehiclesNeverOverlapped = currentDidNotOverlapWithOther && otherDoesNotOverlapWithCurrent;
        bool currentAlwaysFirst = currentIsOriginallyFirst && currentStartsFirstNow;
        bool otherAlwaysOverlaps = otherOverlappedWithCurrent && otherOverlapsNowWithCurrent;
        return check_conditions_to_mark(switchCurrentWithOtherOrder, vehiclesNeverOverlapped,
                                        currentAlwaysFirst, otherAlwaysOverlaps);
    }

    auto
    Scheduler::mark_vehicle(const long otherVehicle,
                            const double otherDeparture,
                            const long otherPosition) -> void {
        _assertOtherIsNotActive(otherVehicle);
        other_trip_departure.trip_id = otherVehicle;
        other_trip_departure.arc_id = departure.arc_id;
        other_trip_departure.time = otherDeparture;
        other_trip_departure.position = otherPosition;
        other_trip_departure.reinsertionNumber = 0;
        other_trip_departure.eventType = Departure::ACTIVATION;
        trip_status_list[otherVehicle] = vehicleStatusType::STAGING;
        pq_departures.push(other_trip_departure);
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


    auto Scheduler::update_vehicle_schedule(Solution &solution,
                                            const double currentNewArrival) const -> void {
        // update departureTime and arrival in new schedule
        solution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
        solution.set_trip_arc_departure(departure.trip_id, departure.position + 1, currentNewArrival);
    }


    auto Scheduler::update_existing_congested_schedule(Solution &completeSolution,
                                                       const Conflict &conflict) -> void {

        initialize_scheduler_for_update_solution(completeSolution.get_schedule());
        initialize_status_vehicles();
        initialize_priority_queue(conflict, completeSolution);
        while (!pq_departures.empty()) {
            departure = pq_departures.top();
            pq_departures.pop();
            const auto skipDeparture = check_if_departure_should_be_skipped();
            if (skipDeparture) { continue; }
            _printDeparture();
            activate_staging_vehicle();
            completeSolution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
            vehicles_to_mark.clear();
            lazy_update_pq = false;
            process_vehicle(completeSolution);
            if (tie_found || trip_is_late) {
                completeSolution.set_feasible_and_improving_flag(false);
                return;
            }
            if (lazy_update_pq) {
                pq_departures.push(departure);
                continue;
            }
        }
        update_total_value_solution(completeSolution);
        if (completeSolution.get_total_delay() >= best_total_delay) {
            worseSolutions++;
            completeSolution.set_feasible_and_improving_flag(false);
        }
        _assertNoVehiclesAreLate(completeSolution);
    }
}
