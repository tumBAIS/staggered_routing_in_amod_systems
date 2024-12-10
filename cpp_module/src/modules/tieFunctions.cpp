#include <iostream>
#include <cmath>
#include "scheduler.h"
#include <queue>


namespace cpp_module {

    struct CorrectSolution {
        VehicleSchedule schedule;
        std::vector<std::vector<bool>> tableWithCapReached;
        double totalDelay;
        bool capIsReached;
        long timesCapIsReached;
        bool scheduleIsFeasibleAndImproving;
    };


    auto _resetSolution(Solution &completeSolution,
                        const long &vehicleOne,
                        const CorrectSolution &correctSolution) -> void {
        staggerVehicle(completeSolution, vehicleOne, -CONSTR_TOLERANCE);
        completeSolution.solutionHasTies = true;
        completeSolution.schedule = correctSolution.schedule;
        completeSolution.total_delay = correctSolution.totalDelay;
        completeSolution.scheduleIsFeasibleAndImproving = correctSolution.scheduleIsFeasibleAndImproving;
        completeSolution.capReached = correctSolution.capIsReached;
        completeSolution.timesCapIsReached = correctSolution.timesCapIsReached;
    }

    auto _checkIfSlackISEnoughToSolveTie(const double slackVehicle) -> bool {
        bool enoughSlackToSolveTie = slackVehicle > CONSTR_TOLERANCE;
        if (!enoughSlackToSolveTie) {
            return false;
        }
        return true;
    };


    auto _setCorrectSolution(const Solution &completeSolution) -> CorrectSolution {
        CorrectSolution correctSolution{};

        correctSolution.schedule = completeSolution.schedule;
        correctSolution.tableWithCapReached = completeSolution.tableWithCapReached;
        correctSolution.totalDelay = completeSolution.total_delay;
        correctSolution.capIsReached = completeSolution.capReached;
        correctSolution.timesCapIsReached = completeSolution.timesCapIsReached;
        return correctSolution;
    }

    auto _printTieSolved(const Tie &tie) -> void {
        std::cout << "Staggering vehicle " << tie.vehicleOne << " of " << CONSTR_TOLERANCE << " [s] to solve";
        std::cout << " tie with vehicle " << tie.vehicleTwo << " on arc " << tie.arc << "\n";
    }

    auto checkIfVehiclesHaveTie(const VehicleSchedule &congestedSchedule,
                                const Tie &tie) -> bool {
        const bool vehiclesDepartAtSameTime = std::abs(
                congestedSchedule[tie.vehicleOne][tie.positionOne] -
                congestedSchedule[tie.vehicleTwo][tie.positionTwo]) < CONSTR_TOLERANCE - 1e-6;
        const bool vehicleOneArrivesAtVehicleTwoDeparture = std::abs(
                congestedSchedule[tie.vehicleTwo][tie.positionTwo] -
                congestedSchedule[tie.vehicleOne][tie.positionOne + 1]) < CONSTR_TOLERANCE - 1e-6;;
        const bool vehicleTwoArrivesAtVehicleOneDeparture = std::abs(
                congestedSchedule[tie.vehicleOne][tie.positionOne] -
                congestedSchedule[tie.vehicleTwo][tie.positionTwo + 1]) < CONSTR_TOLERANCE - 1e-6;;
        bool thereIsTie = vehiclesDepartAtSameTime || vehicleOneArrivesAtVehicleTwoDeparture ||
                          vehicleTwoArrivesAtVehicleOneDeparture;
        return thereIsTie;
    }

    auto _solveTie(Solution &completeSolution, const Tie &tie, Scheduler &scheduler) -> void {
        auto thereIsTie = checkIfVehiclesHaveTie(completeSolution.schedule, tie);
        auto slackIsEnough = _checkIfSlackISEnoughToSolveTie(completeSolution.remainingTimeSlack[tie.vehicleOne]);
        while (thereIsTie && slackIsEnough) {
            const CorrectSolution correctSolution = _setCorrectSolution(completeSolution);
            staggerVehicle(completeSolution, tie.vehicleOne, CONSTR_TOLERANCE);
            scheduler.construct_schedule(completeSolution);
            if (!completeSolution.scheduleIsFeasibleAndImproving) {
                _resetSolution(completeSolution, tie.vehicleOne, correctSolution);

                return;
            }
            _printTieSolved(tie);
            thereIsTie = checkIfVehiclesHaveTie(completeSolution.schedule, tie);
            slackIsEnough = _checkIfSlackISEnoughToSolveTie(completeSolution.remainingTimeSlack[tie.vehicleOne]);
        }
    }

    auto _checkArcTies(const Instance &instance,
                       const long &arc,
                       Solution &completeSolution) -> bool {
        Tie tie{};
        for (auto vehicleOne: instance.conflictingSet[arc]) {
            const long positionOne = getIndex(instance.trip_routes[vehicleOne], arc);
            for (auto vehicleTwo: instance.conflictingSet[arc]) {
                if (vehicleOne < vehicleTwo) {
                    const long positionTwo = getIndex(instance.trip_routes[vehicleTwo], arc);
                    tie = {vehicleOne, vehicleTwo, positionOne, positionTwo, arc};
                    bool tieOnArc = checkIfVehiclesHaveTie(completeSolution.schedule, tie);
                    if (tieOnArc) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    auto _solveArcTies(const Instance &instance,
                       const long &arc,
                       Solution &completeSolution,
                       Scheduler &scheduler) {
        Tie tie{};
        for (auto vehicleOne: instance.conflictingSet[arc]) {
            const long positionOne = getIndex(instance.trip_routes[vehicleOne], arc);
            for (auto vehicleTwo: instance.conflictingSet[arc]) {
                if (vehicleOne != vehicleTwo) {
                    const long positionTwo = getIndex(instance.trip_routes[vehicleTwo], arc);
                    tie = {vehicleOne, vehicleTwo, positionOne, positionTwo, arc};
                    _solveTie(completeSolution, tie, scheduler);
                }
            }
        }
    }

    auto _printIfSolutionHasTies(const Solution &currentSolution) -> void {
#ifdef assertionsOnEvaluationFunction
        if (currentSolution.solutionHasTies) {
            std::cout << "Solution has ties! \n";
        }
#endif
    }

    auto checkIfSolutionHasTies(const Instance &instance, Solution &completeSolution) -> void {
        for (long arc = 1; arc < instance.numberOfArcs; arc++) {
            bool noTiesCanHappenOnArc = instance.conflictingSet[arc].empty();
            if (noTiesCanHappenOnArc) {
                continue;
            }
            bool thereIsTie = _checkArcTies(instance, arc, completeSolution);
            if (thereIsTie) {
                completeSolution.solutionHasTies = true;
                _printIfSolutionHasTies(completeSolution);
                return;
            }
            completeSolution.solutionHasTies = false;
        }
    }


    auto solveSolutionTies(const Instance &instance, Solution &completeSolution, Scheduler &scheduler) -> void {
        completeSolution.solutionHasTies = false; // will be set to true if a tie cannot be solved
        for (long arc = 1; arc < instance.numberOfArcs; arc++) {
            bool noTiesCanHappenOnArc = instance.conflictingSet[arc].empty();
            if (noTiesCanHappenOnArc) {
                continue;
            }
            _solveArcTies(instance, arc, completeSolution, scheduler);
        }
    }


}

