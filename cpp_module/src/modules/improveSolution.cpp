#include <numeric>
#include <iostream>
#include <iomanip>
#include <cmath>
#include "scheduler.h"
#include <queue>
#include <cassert>
#include <chrono>

namespace cpp_module {

    auto staggerVehicle(Solution &completeSolution, long vehicle, double staggering) -> void {
        completeSolution.increase_trip_start_time(vehicle, staggering);
        completeSolution.increase_staggering_applied(vehicle, staggering);
        completeSolution.increase_remaining_time_slack(vehicle, -staggering); //staggering is negative
    }

    auto checkIfTimeLimitIsReached(const double startSearchClock, double maxTimeOptimization) -> bool {
        auto timeNow = clock() / (double) CLOCKS_PER_SEC;
        auto duration = (timeNow - startSearchClock);
        if (duration > maxTimeOptimization) {
            std::cout << "STOPPING LOCAL SEARCH - MAX TIME LIMIT REACHED \n";
            return true;
        }
        return false;
    }


    auto _resetNewSolution(const Solution &currentSolution, Solution &newSolution,
                           Conflict &conflict) -> void {
        staggerVehicle(newSolution,
                       conflict.current_trip_id,
                       -conflict.staggeringCurrentVehicle);
        conflict.staggeringCurrentVehicle = 0;
        staggerVehicle(newSolution,
                       conflict.other_trip_id,
                       conflict.destaggeringOtherVehicle);
        conflict.destaggeringOtherVehicle = 0;
        newSolution.set_schedule(currentSolution.get_schedule());
        newSolution.set_total_delay(currentSolution.get_total_delay());
        newSolution.set_ties_flag(currentSolution.get_ties_flag());
        newSolution.set_feasible_and_improving_flag(currentSolution.get_feasible_and_improving_flag());
    }

    auto _applyStaggeringToSolveConflict(Scheduler &scheduler,
                                         Solution &completeSolution,
                                         Conflict &conflict) -> void {
        assert(conflict.distanceToCover > 0);
        bool moveVehicleOne =
                conflict.distanceToCover < completeSolution.get_trip_remaining_time_slack(conflict.current_trip_id);
        bool moveBothVehicles =
                conflict.distanceToCover < completeSolution.get_trip_remaining_time_slack(conflict.current_trip_id) +
                                           completeSolution.get_trip_staggering_applied(conflict.other_trip_id);
        if (moveVehicleOne) {
            staggerVehicle(completeSolution, conflict.current_trip_id, conflict.distanceToCover);
            conflict.staggeringCurrentVehicle += conflict.distanceToCover;
            assert(conflict.distanceToCover > 0);
        } else if (moveBothVehicles) {
            // distance can be covered removing staggering to other vehicle
            auto staggering = std::max(0.0, completeSolution.get_trip_remaining_time_slack(conflict.current_trip_id));
            auto destaggering = conflict.distanceToCover - staggering;
            staggerVehicle(completeSolution, conflict.current_trip_id, staggering);
            staggerVehicle(completeSolution, conflict.other_trip_id, -destaggering);
            conflict.staggeringCurrentVehicle += staggering;
            conflict.destaggeringOtherVehicle += destaggering;
            assert(staggering > 0 || destaggering > 0);
        } else {
            throw std::invalid_argument("Applying staggering to solve conflict - undefined case");
        }
    }

    auto _updateCurrentSolution(Solution &currentSolution,
                                const Solution &newSolution,
                                Conflict &conflict) -> void {
        // update current vehicle
        staggerVehicle(currentSolution, conflict.current_trip_id, conflict.staggeringCurrentVehicle);
        staggerVehicle(currentSolution, conflict.other_trip_id, -conflict.destaggeringOtherVehicle);
        currentSolution.set_schedule(newSolution.get_schedule());
        currentSolution.set_total_delay(newSolution.get_total_delay());
        currentSolution.set_ties_flag(newSolution.get_ties_flag());
        currentSolution.set_feasible_and_improving_flag(newSolution.get_feasible_and_improving_flag());
    }

    auto _printMove(const Solution &oldSolution,
                    const Solution &newSolution,
                    const Conflict &conflict) -> void {
        if (std::abs(oldSolution.get_total_delay() - newSolution.get_total_delay()) > TOLERANCE) {
            if (conflict.staggeringCurrentVehicle > 0) {
                std::cout << std::fixed << std::setprecision(2) << " - staggering " << conflict.current_trip_id
                          << " by "
                          << conflict.staggeringCurrentVehicle;
            }
            if (conflict.destaggeringOtherVehicle > 0) {
                std::cout << std::fixed << std::setprecision(2) << " - destaggering " << conflict.other_trip_id
                          << " by "
                          << conflict.destaggeringOtherVehicle;
            }
            std::cout << std::fixed << std::setprecision(2) << " - DELnew: "
                      << newSolution.get_total_delay() << " -> DELold - DELnew = "
                      << oldSolution.get_total_delay() - newSolution.get_total_delay();
            std::cout << std::endl;
        }

    }


    auto _updateDistanceToCover(const Solution &completeSolution,
                                Conflict &conflict,
                                const Instance &instance) -> void {
        auto indexArcInPathCurrentVehicle = getIndex(instance.trip_routes[conflict.current_trip_id],
                                                     conflict.arc);
        auto indexArcInPathOtherVehicle = getIndex(instance.trip_routes[conflict.other_trip_id],
                                                   conflict.arc);

        conflict.distanceToCover =
                completeSolution.get_trip_arc_departure(conflict.other_trip_id, indexArcInPathOtherVehicle + 1) -
                completeSolution.get_trip_arc_departure(conflict.current_trip_id, indexArcInPathCurrentVehicle) -
                CONSTR_TOLERANCE;
    }

    auto _checkIfPossibleToSolveConflict(const double &distanceToCover,
                                         const double &slackVehicleOne,
                                         const double &staggeringAppliedVehicleTwo) {
        if (slackVehicleOne + staggeringAppliedVehicleTwo > distanceToCover) {
            return true;
        }

        return false;
    }

    auto _checkIfSolutionIsAdmissible(const Instance &instance,
                                      Solution &completeSolution,
                                      Scheduler &scheduler) -> bool {
        if (!completeSolution.get_feasible_and_improving_flag()) {
            return false;
        }
        if (completeSolution.get_ties_flag()) {
            scheduler.solutionWithTies++;
            return false;
        }
        return true;
    }

    auto _solveConflict(Conflict &conflict, Solution &newSolution,
                        const Instance &instance, Scheduler &scheduler) {
        scheduler.exploredSolutions++;
        bool conflictIsNotSolved = conflict.distanceToCover > CONSTR_TOLERANCE;
        while (conflictIsNotSolved) {
            bool timeLimitReached = checkIfTimeLimitIsReached(scheduler.startSearchClock,
                                                              instance.maxTimeOptimization);
            if (timeLimitReached) {
                break;
            }
            scheduler.slackIsEnough =
                    _checkIfPossibleToSolveConflict(conflict.distanceToCover,
                                                    newSolution.get_trip_remaining_time_slack(conflict.current_trip_id),
                                                    newSolution.get_trip_staggering_applied(conflict.other_trip_id));
            if (!scheduler.slackIsEnough) {
                scheduler.slackNotEnough++; // printing purposes
                break;
            }
            _applyStaggeringToSolveConflict(scheduler, newSolution, conflict);
            scheduler.updateExistingCongestedSchedule(newSolution, conflict);
            if (!newSolution.get_feasible_and_improving_flag()) { break; }
            _updateDistanceToCover(newSolution, conflict, instance);
            conflictIsNotSolved = conflict.distanceToCover > CONSTR_TOLERANCE;
        }
    }

    auto _improveSolution(const Instance &instance,
                          const std::vector<Conflict> &conflictsList,
                          Scheduler &scheduler,
                          Solution &currentSolution) -> bool {
        Solution newSolution(currentSolution);
        for (auto conflict: conflictsList) {
            if (std::abs(conflict.distanceToCover) < 1e-6) {
                continue;
            }
            _solveConflict(conflict, newSolution, instance, scheduler);
            bool timeLimitReached = checkIfTimeLimitIsReached(scheduler.startSearchClock, instance.maxTimeOptimization);
            if (timeLimitReached) {
                return false;
            }
            bool isAdmissible = _checkIfSolutionIsAdmissible(instance, newSolution, scheduler);
            if (isAdmissible && scheduler.slackIsEnough) {
                if (scheduler.iteration % 20 == 0) {
                    scheduler.construct_schedule(newSolution);
                }
                _printMove(currentSolution, newSolution, conflict);
                _updateCurrentSolution(currentSolution, newSolution, conflict);
                _assertSolutionIsCorrect(newSolution, scheduler);
                return true;
            } else {
                _resetNewSolution(currentSolution, newSolution, conflict);
                continue;
            }
        }
        return false;
    }


    auto improveTowardsSolutionQuality(const Instance &instance,
                                       Solution &currentSolution,
                                       Scheduler &scheduler) -> void {
        // improve value of solution
        ConflictSearcherNew conflictSearcher(instance);
        bool isImproved = true;
        while (isImproved) { //initially set to true
            bool timeLimitReached = checkIfTimeLimitIsReached(scheduler.startSearchClock, instance.maxTimeOptimization);
            if (timeLimitReached) { break; }
            scheduler.best_total_delay = currentSolution.get_total_delay();
            auto conflictsList = conflictSearcher.getConflictsListNew(currentSolution.get_schedule());
            _sortConflicts(conflictsList);
            if (conflictsList.empty()) { break; }
            isImproved = _improveSolution(instance, conflictsList, scheduler, currentSolution);
        }
        scheduler.construct_schedule(currentSolution);
    }


}