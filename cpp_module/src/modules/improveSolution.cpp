#include <numeric>
#include <iostream>
#include <iomanip>
#include <cmath>
#include "module.h"
#include <queue>
#include <cassert>
#include <chrono>

namespace cpp_module {

    auto staggerVehicle(Solution &completeSolution, long vehicle, double staggering) -> void {
        completeSolution.start_times[vehicle] += staggering;
        completeSolution.staggeringApplied[vehicle] += staggering;
        completeSolution.remainingTimeSlack[vehicle] -= staggering;
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
                       conflict.currentVehicle,
                       -conflict.staggeringCurrentVehicle);
        conflict.staggeringCurrentVehicle = 0;
        staggerVehicle(newSolution,
                       conflict.otherVehicle,
                       conflict.destaggeringOtherVehicle);
        conflict.destaggeringOtherVehicle = 0;
        newSolution.schedule = currentSolution.schedule;
        newSolution.total_delay = currentSolution.total_delay;
        newSolution.totalTardiness = currentSolution.totalTardiness;
        newSolution.solutionValue = currentSolution.solutionValue;
        newSolution.solutionHasTies = currentSolution.solutionHasTies;
        newSolution.capReached = currentSolution.capReached;
        newSolution.timesCapIsReached = currentSolution.timesCapIsReached;
        newSolution.scheduleIsFeasibleAndImproving = currentSolution.scheduleIsFeasibleAndImproving;
        newSolution.tableWithCapReached = currentSolution.tableWithCapReached;
    }

    auto _applyStaggeringToSolveConflict(Scheduler &scheduler,
                                         Solution &completeSolution,
                                         Conflict &conflict) -> void {
        assert(conflict.distanceToCover > 0);
        bool moveVehicleOne =
                conflict.distanceToCover < completeSolution.remainingTimeSlack[conflict.currentVehicle];
        bool moveBothVehicles =
                conflict.distanceToCover < completeSolution.remainingTimeSlack[conflict.currentVehicle] +
                                           completeSolution.staggeringApplied[conflict.otherVehicle];
        if (moveVehicleOne) {
            staggerVehicle(completeSolution, conflict.currentVehicle, conflict.distanceToCover);
            conflict.staggeringCurrentVehicle += conflict.distanceToCover;
            assert(conflict.distanceToCover > 0);
        } else if (moveBothVehicles) {
            // distance can be covered removing staggering to other vehicle
            auto staggering = std::max(0.0, completeSolution.remainingTimeSlack[conflict.currentVehicle]);
            auto destaggering = conflict.distanceToCover - staggering;
            staggerVehicle(completeSolution, conflict.currentVehicle, staggering);
            staggerVehicle(completeSolution, conflict.otherVehicle, -destaggering);
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
        staggerVehicle(currentSolution, conflict.currentVehicle, conflict.staggeringCurrentVehicle);
        staggerVehicle(currentSolution, conflict.otherVehicle, -conflict.destaggeringOtherVehicle);
        currentSolution.schedule = newSolution.schedule;
        currentSolution.total_delay = newSolution.total_delay;
        currentSolution.totalTardiness = newSolution.totalTardiness;
        currentSolution.solutionValue = newSolution.solutionValue;
        currentSolution.solutionHasTies = newSolution.solutionHasTies;
        currentSolution.capReached = newSolution.capReached;
        currentSolution.timesCapIsReached = newSolution.timesCapIsReached;
        currentSolution.scheduleIsFeasibleAndImproving = newSolution.scheduleIsFeasibleAndImproving;
        currentSolution.tableWithCapReached = newSolution.tableWithCapReached;
    }

    auto _printMove(const Solution &oldSolution,
                    const Solution &newSolution,
                    const Conflict &conflict) -> void {
        if (std::abs(oldSolution.solutionValue - newSolution.solutionValue) > TOLERANCE) {
            if (conflict.staggeringCurrentVehicle > 0) {
                std::cout << std::fixed << std::setprecision(2) << " - staggering " << conflict.currentVehicle << " by "
                          << conflict.staggeringCurrentVehicle;
            }
            if (conflict.destaggeringOtherVehicle > 0) {
                std::cout << std::fixed << std::setprecision(2) << " - destaggering " << conflict.otherVehicle << " by "
                          << conflict.destaggeringOtherVehicle;
            }
            std::cout << std::fixed << std::setprecision(2) << " - DELnew: "
                      << newSolution.total_delay << " -> DELold - DELnew = "
                      << oldSolution.total_delay - newSolution.total_delay;
            std::cout << std::endl;
        }

    }


    auto _updateDistanceToCover(const Solution &completeSolution,
                                Conflict &conflict,
                                const Instance &instance) -> void {
        auto indexArcInPathCurrentVehicle = getIndex(instance.trip_routes[conflict.currentVehicle],
                                                     conflict.arc);
        auto indexArcInPathOtherVehicle = getIndex(instance.trip_routes[conflict.otherVehicle],
                                                   conflict.arc);

        conflict.distanceToCover =
                completeSolution.schedule[conflict.otherVehicle][indexArcInPathOtherVehicle + 1] -
                completeSolution.schedule[conflict.currentVehicle][indexArcInPathCurrentVehicle] -
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
        if (!completeSolution.scheduleIsFeasibleAndImproving) {
            return false;
        }
        if (completeSolution.solutionHasTies) {
            scheduler.solutionWithTies++;
            return false;
        }
        if (completeSolution.timesCapIsReached > scheduler.maxTimesCapReached) {
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
                                                    newSolution.remainingTimeSlack[conflict.currentVehicle],
                                                    newSolution.staggeringApplied[conflict.otherVehicle]);
            if (!scheduler.slackIsEnough) {
                scheduler.slackNotEnough++; // printing purposes
                break;
            }
            _applyStaggeringToSolveConflict(scheduler, newSolution, conflict);
            scheduler.updateExistingCongestedSchedule(newSolution, conflict);
            if (!newSolution.scheduleIsFeasibleAndImproving) { break; }
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
            scheduler.bestSolutionValue = currentSolution.solutionValue;
            auto conflictsList = conflictSearcher.getConflictsListNew(currentSolution.schedule);
            _sortConflicts(conflictsList);
            if (conflictsList.empty()) { break; }
            isImproved = _improveSolution(instance, conflictsList, scheduler, currentSolution);
        }
        scheduler.construct_schedule(currentSolution);
    }


}