#include <numeric>
#include <algorithm>
#include <iostream>
#include <cmath>
#include "module.h"
#include <queue>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>


namespace cppModule {

    auto _printIfAssertionsAreActive() -> void {
#ifdef assertionsOnEvaluationFunction
        std::cout << "Assertions on evaluation function activated \n";
#endif
#ifdef assertionsOnMoveOperator
        std::cout << "Assertions on move operator activated \n";
#endif
    }


    auto cppComputeCongestedSchedule(const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                     const std::vector<double> &argReleaseTimes,
                                     const std::vector<double> &nominalTravelTimesArcs,
                                     const std::vector<long> &nominalCapacitiesArcsUtilized,
                                     const std::vector<double> &arg_list_of_slopes,
                                     const std::vector<double> &arg_list_of_thresholds,
                                     const std::vector<double> &parameters
    ) -> VehicleSchedule {
        _printIfAssertionsAreActive();
        // Function computing schedule with congestion given set of release times.
        Instance instance(arcBasedShortestPaths,
                          nominalTravelTimesArcs,
                          nominalCapacitiesArcsUtilized,
                          arg_list_of_slopes,
                          arg_list_of_thresholds,
                          parameters);
        CompleteSolution completeSolution(argReleaseTimes, instance);
        Scheduler schedulerForPython(instance);
        schedulerForPython.constructCongestedSchedule(completeSolution);
        initializeConflictingSetsForConstructSchedule(instance);
        checkIfSolutionHasTies(instance, completeSolution);
        if (completeSolution.solutionHasTies) {
            solveSolutionTies(instance, completeSolution, schedulerForPython);
        }
        return completeSolution.congestedSchedule;
    }

    auto addTotalFFTTVehicles(Instance &instance) -> void {
        for (auto vehicle = 0; vehicle < instance.numberOfVehicles; vehicle++) {
            for (auto arc: instance.arcBasedShortestPaths[vehicle]) {
                instance.freeFlowTravelTimesVehicles[vehicle] += instance.nominalTravelTimesArcs[arc];
            }
        }
    }

    auto getInstanceForLocalSearch(const PotentiallyConflictingVehiclesSets &argConflictingSets,
                                   const std::vector<std::vector<double>> &earliestDepartureTimes,
                                   const std::vector<std::vector<double>> &latestDepartureTimes,
                                   const std::vector<double> &nominalTravelTimesArcs,
                                   const std::vector<long> &nominalCapacitiesArcsUtilized,
                                   const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                   const std::vector<double> &argDeadlines,
                                   const std::vector<double> &argDueDates,
                                   const std::vector<double> &arg_list_of_slopes,
                                   const std::vector<double> &arg_list_of_thresholds,
                                   const std::vector<double> &argParameters) -> Instance {
        Instance instance(arcBasedShortestPaths,
                          nominalTravelTimesArcs,
                          nominalCapacitiesArcsUtilized,
                          arg_list_of_slopes,
                          arg_list_of_thresholds,
                          argParameters);
        instance.deadlines = argDeadlines;
        instance.dueDates = argDueDates;
        instance.conflictingSet = argConflictingSets;
        instance.earliestDepartureTimes = earliestDepartureTimes;
        instance.latestDepartureTimes = latestDepartureTimes;
        addTotalFFTTVehicles(instance);
        return instance;
    }


    auto getInitialSolutionForLocalSearch(Scheduler &scheduler,
                                          const Instance &instance,
                                          const std::vector<double> &argReleaseTimes,
                                          const std::vector<double> &argRemainingTimeSlack,
                                          const std::vector<double> &argStaggeringApplied) -> CompleteSolution {
        CompleteSolution currentSolution(argReleaseTimes, instance);
        scheduler.constructCongestedSchedule(currentSolution);
        if (!currentSolution.scheduleIsFeasibleAndImproving) {
            std::cout << "Initial solution is infeasible - local search stopped \n";
            return currentSolution;
        }
        currentSolution.remainingTimeSlack = argRemainingTimeSlack;
        currentSolution.staggeringApplied = argStaggeringApplied;
        return currentSolution;
    }

    auto cppSchedulingLocalSearch(const std::vector<double> &argReleaseTimes,
                                  const std::vector<double> &argRemainingTimeSlack,
                                  const std::vector<double> &argStaggeringApplied,
                                  const PotentiallyConflictingVehiclesSets &argConflictingSets,
                                  const std::vector<std::vector<double>> &earliestDepartureTimes,
                                  const std::vector<std::vector<double>> &latestDepartureTimes,
                                  const std::vector<double> &argNominalTravelTimesArcs,
                                  const std::vector<long> &argNominalCapacitiesArcsUtilized,
                                  const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                  const std::vector<double> &argDeadlines,
                                  const std::vector<double> &argDueDates,
                                  const std::vector<double> &arg_list_of_slopes,
                                  const std::vector<double> &arg_list_of_thresholds,
                                  const std::vector<double> &argParameters) -> VehicleSchedule {
        Instance instance = getInstanceForLocalSearch(argConflictingSets,
                                                      earliestDepartureTimes,
                                                      latestDepartureTimes,
                                                      argNominalTravelTimesArcs,
                                                      argNominalCapacitiesArcsUtilized,
                                                      arcBasedShortestPaths,
                                                      argDeadlines,
                                                      argDueDates,
                                                      arg_list_of_slopes,
                                                      arg_list_of_thresholds,
                                                      argParameters);
        if (instance.dueDates.size() != instance.deadlines.size()) {
            throw std::invalid_argument("due dates are invalid");
        }
        Scheduler scheduler(instance);
        CompleteSolution currentSolution = getInitialSolutionForLocalSearch(scheduler, instance,
                                                                            argReleaseTimes, argRemainingTimeSlack,
                                                                            argStaggeringApplied);
        std::cout << "Local search received a solution with " << std::round(currentSolution.totalDelay)
                  << " sec. of delay \n";
        if (!currentSolution.scheduleIsFeasibleAndImproving) {
            return currentSolution.congestedSchedule;
        }
        checkIfSolutionHasTies(instance, currentSolution);
        if (currentSolution.solutionHasTies) {
            solveSolutionTies(instance, currentSolution, scheduler);
        }
        improveTowardsSolutionQuality(instance, currentSolution, scheduler);

        return currentSolution.congestedSchedule;
    } // end local_search function
}


PYBIND11_MODULE(cpp_module, m) {
    m.doc() = "CPP module";
    m.def("cppComputeCongestedSchedule", &cppModule::cppComputeCongestedSchedule);
    m.def("cppSchedulingLocalSearch", &cppModule::cppSchedulingLocalSearch);
}
