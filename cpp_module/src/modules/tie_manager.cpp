#include <iostream>
#include <cmath>
#include "scheduler.h"
#include <queue>


namespace cpp_module {

    struct CorrectSolution {
        VehicleSchedule schedule;
        std::vector<std::vector<bool>> tableWithCapReached;
        double totalDelay;
        long timesCapIsReached;
        bool scheduleIsFeasibleAndImproving;
    };


    auto _resetSolution(Solution &completeSolution,
                        const long &vehicleOne,
                        const CorrectSolution &correctSolution) -> void {
        staggerVehicle(completeSolution, vehicleOne, -CONSTR_TOLERANCE);
        completeSolution.set_ties_flag(true);
        completeSolution.set_schedule(correctSolution.schedule);
        completeSolution.set_total_delay(correctSolution.totalDelay);
        completeSolution.set_feasible_and_improving_flag(correctSolution.scheduleIsFeasibleAndImproving);
    }

    auto _checkIfSlackISEnoughToSolveTie(const double slackVehicle) -> bool {
        bool enoughSlackToSolveTie = slackVehicle > CONSTR_TOLERANCE;
        if (!enoughSlackToSolveTie) {
            return false;
        }
        return true;
    }


    auto _setCorrectSolution(const Solution &completeSolution) -> CorrectSolution {
        CorrectSolution correctSolution{};

        correctSolution.schedule = completeSolution.get_schedule();
        correctSolution.totalDelay = completeSolution.get_total_delay();
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
                congestedSchedule[tie.vehicleOne][tie.positionOne + 1]) < CONSTR_TOLERANCE - 1e-6;
        const bool vehicleTwoArrivesAtVehicleOneDeparture = std::abs(
                congestedSchedule[tie.vehicleOne][tie.positionOne] -
                congestedSchedule[tie.vehicleTwo][tie.positionTwo + 1]) < CONSTR_TOLERANCE - 1e-6;
        bool thereIsTie = vehiclesDepartAtSameTime || vehicleOneArrivesAtVehicleTwoDeparture ||
                          vehicleTwoArrivesAtVehicleOneDeparture;
        return thereIsTie;
    }

    auto _solveTie(Solution &completeSolution, const Tie &tie, Scheduler &scheduler) -> void {
        auto thereIsTie = checkIfVehiclesHaveTie(completeSolution.get_schedule(), tie);
        auto slackIsEnough = _checkIfSlackISEnoughToSolveTie(
                completeSolution.get_trip_remaining_time_slack(tie.vehicleOne));
        while (thereIsTie && slackIsEnough) {
            const CorrectSolution correctSolution = _setCorrectSolution(completeSolution);
            staggerVehicle(completeSolution, tie.vehicleOne, CONSTR_TOLERANCE);
            scheduler.construct_schedule(completeSolution);
            if (!completeSolution.get_feasible_and_improving_flag()) {
                _resetSolution(completeSolution, tie.vehicleOne, correctSolution);

                return;
            }
            _printTieSolved(tie);
            thereIsTie = checkIfVehiclesHaveTie(completeSolution.get_schedule(), tie);
            slackIsEnough = _checkIfSlackISEnoughToSolveTie(
                    completeSolution.get_trip_remaining_time_slack(tie.vehicleOne));
        }
    }

    auto _checkArcTies(const Instance &instance,
                       const ArcID &arc_id,
                       Solution &completeSolution) -> bool {
        Tie tie{};
        for (auto first_trip: instance.get_conflicting_set(arc_id)) {
            const long positionOne = get_index(instance.get_trip_route(first_trip), arc_id);
            for (auto second_trip: instance.get_conflicting_set(arc_id)) {
                if (first_trip < second_trip) {
                    const long positionTwo = get_index(instance.get_trip_route(second_trip), arc_id);
                    tie = {first_trip, second_trip, positionOne, positionTwo, arc_id};
                    bool tieOnArc = checkIfVehiclesHaveTie(completeSolution.get_schedule(), tie);
                    if (tieOnArc) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    auto _solveArcTies(const Instance &instance,
                       const long &arc_id,
                       Solution &completeSolution,
                       Scheduler &scheduler) {
        Tie tie{};
        for (auto first_trip: instance.get_conflicting_set(arc_id)) {
            const long positionOne = get_index(instance.get_trip_route(first_trip), arc_id);
            for (auto second_trip: instance.get_conflicting_set(arc_id)) {
                if (first_trip != second_trip) {
                    const long positionTwo = get_index(instance.get_trip_route(second_trip), arc_id);
                    tie = {first_trip, second_trip, positionOne, positionTwo, arc_id};
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

    auto check_if_solution_has_ties(const Instance &instance, Solution &completeSolution) -> void {
        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); arc_id++) {
            bool noTiesCanHappenOnArc = instance.get_conflicting_set(arc_id).empty();
            if (noTiesCanHappenOnArc) {
                continue;
            }
            bool thereIsTie = _checkArcTies(instance, arc_id, completeSolution);
            if (thereIsTie) {
                completeSolution.set_ties_flag(true);
                _printIfSolutionHasTies(completeSolution);
                return;
            }
            completeSolution.set_ties_flag(false);
        }
    }


    auto solve_solution_ties(const Instance &instance, Solution &completeSolution, Scheduler &scheduler) -> void {
        completeSolution.set_ties_flag(false); // will be set to true if a tie cannot be solved
        for (long arc_id = 1; arc_id < instance.get_number_of_arcs(); arc_id++) {
            bool noTiesCanHappenOnArc = instance.get_conflicting_set(arc_id).empty();
            if (noTiesCanHappenOnArc) {
                continue;
            }
            _solveArcTies(instance, arc_id, completeSolution, scheduler);
        }
    }


}

