#include <algorithm>
#include <iostream>
#include <cmath>
#include "scheduler.h"
#include <queue>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>


namespace cpp_module {

    auto _printIfAssertionsAreActive() -> void {
#ifdef assertionsOnEvaluationFunction
        std::cout << "Assertions on evaluation function activated \n";
#endif
#ifdef assertionsOnMoveOperator
        std::cout << "Assertions on move operator activated \n";
#endif
    }


    auto Scheduler::construct_solution(const std::vector<double> &start_times) -> Solution {
        _printIfAssertionsAreActive();
        // Function computing schedule with congestion given set of release times.
        Solution completeSolution(start_times, instance);
        construct_schedule(completeSolution);
        initialize_conflicting_sets_for_construct_schedule(instance);
        checkIfSolutionHasTies(instance, completeSolution);
        if (completeSolution.get_ties_flag()) {
            solveSolutionTies(instance, completeSolution, *this);
        }
        return completeSolution;
    }

    auto addTotalFFTTVehicles(Instance &instance) -> void {
        for (auto trip_id = 0; trip_id < instance.get_number_of_trips(); trip_id++) {
            for (auto arc: instance.get_trip_route(trip_id)) {
                instance.increase_free_flow_travel_time_trip(trip_id, instance.get_arc_travel_time(arc));
            }
        }
    }

    auto getInstanceForLocalSearch(const ConflictingSetsList &argConflictingSets,
                                   const std::vector<std::vector<double>> &earliestDepartureTimes,
                                   const std::vector<std::vector<double>> &latestDepartureTimes,
                                   const std::vector<double> &nominalTravelTimesArcs,
                                   const std::vector<long> &nominalCapacitiesArcsUtilized,
                                   const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                   const std::vector<double> &argDeadlines,
                                   const std::vector<double> &argDueDates,
                                   const std::vector<double> &arg_list_of_slopes,
                                   const std::vector<double> &arg_list_of_thresholds,
                                   const std::vector<double> &argParameters,
                                   const std::vector<double> &arg_release_times,
                                   const double &arg_lb_travel_time) -> Instance {
        Instance instance(arcBasedShortestPaths,
                          nominalTravelTimesArcs,
                          nominalCapacitiesArcsUtilized,
                          arg_list_of_slopes,
                          arg_list_of_thresholds,
                          argParameters,
                          arg_release_times,
                          arg_lb_travel_time);
        instance.set_deadlines(argDeadlines);
        instance.set_conflicting_sets(argConflictingSets);
        instance.set_earliest_departure_times(earliestDepartureTimes);
        instance.set_latest_departure_times(latestDepartureTimes);
        addTotalFFTTVehicles(instance);
        return instance;
    }


    auto getInitialSolutionForLocalSearch(Scheduler &scheduler,
                                          Instance &instance,
                                          const std::vector<double> &argReleaseTimes,
                                          const std::vector<double> &argRemainingTimeSlack,
                                          const std::vector<double> &argStaggeringApplied) -> Solution {
        Solution currentSolution(argReleaseTimes, instance);
        scheduler.construct_schedule(currentSolution);
        if (!currentSolution.get_feasible_and_improving_flag()) {
            std::cout << "Initial solution is infeasible - local search stopped \n";
            return currentSolution;
        }
        currentSolution.set_remaining_time_slack(argRemainingTimeSlack);
        currentSolution.set_staggering_applied(argStaggeringApplied);
        return currentSolution;
    }

    auto cppSchedulingLocalSearch(const std::vector<double> &arg_release_times,
                                  const std::vector<double> &argRemainingTimeSlack,
                                  const std::vector<double> &argStaggeringApplied,
                                  const ConflictingSetsList &argConflictingSets,
                                  const std::vector<std::vector<double>> &earliestDepartureTimes,
                                  const std::vector<std::vector<double>> &latestDepartureTimes,
                                  const std::vector<double> &argNominalTravelTimesArcs,
                                  const std::vector<long> &argNominalCapacitiesArcsUtilized,
                                  const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                  const std::vector<double> &argDeadlines,
                                  const std::vector<double> &argDueDates,
                                  const std::vector<double> &arg_list_of_slopes,
                                  const std::vector<double> &arg_list_of_thresholds,
                                  const std::vector<double> &argParameters,
                                  const double &arg_lb_travel_time) -> VehicleSchedule {
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
                                                      argParameters,
                                                      arg_release_times,
                                                      arg_lb_travel_time);
        Scheduler scheduler(instance);
        Solution currentSolution = getInitialSolutionForLocalSearch(scheduler, instance,
                                                                    arg_release_times, argRemainingTimeSlack,
                                                                    argStaggeringApplied);
        std::cout << "Local search received a solution with " << std::round(currentSolution.get_total_delay())
                  << " sec. of delay \n";
        if (!currentSolution.get_feasible_and_improving_flag()) {
            return currentSolution.get_schedule();
        }
        checkIfSolutionHasTies(instance, currentSolution);
        if (currentSolution.get_ties_flag()) {
            solveSolutionTies(instance, currentSolution, scheduler);
        }
        improveTowardsSolutionQuality(instance, currentSolution, scheduler);

        return currentSolution.get_schedule();
    } // end local_search function
}

namespace py = pybind11;

PYBIND11_MODULE(cpp_module, m) {
    m.doc() = "CPP module";
    py::class_<cpp_module::Solution>(m, "cpp_solution")
            .def(py::init<const std::vector<double> &, cpp_module::Instance &>(),
                 py::arg("start_times"),
                 py::arg("cpp_instance"))
            .def("get_trip_schedule", &cpp_module::Solution::get_trip_schedule,
                 py::arg("trip_id"))
            .def("get_schedule", &cpp_module::Solution::get_schedule)
            .def("get_start_times", &cpp_module::Solution::get_start_times)
            .def("get_delays_on_arcs", &cpp_module::Solution::get_delays_on_arcs)
            .def("get_total_delay", &cpp_module::Solution::get_total_delay)
            .def("get_total_travel_time", &cpp_module::Solution::get_total_travel_time);

    py::class_<cpp_module::Instance>(m, "cpp_instance")
            .def(py::init<const std::vector<std::vector<long>> &,
                         const std::vector<double> &,
                         const std::vector<long> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const double &>(),
                 py::arg("set_of_vehicle_paths"),
                 py::arg("travel_times_arcs"),
                 py::arg("capacities_arcs"),
                 py::arg("list_of_slopes"),
                 py::arg("list_of_thresholds"),
                 py::arg("parameters"),
                 py::arg("release_times"),
                 py::arg("lb_travel_time"))
            .def("get_trip_routes", &cpp_module::Instance::get_trip_routes)
            .def("get_travel_times_arcs", &cpp_module::Instance::get_travel_times_arcs)
            .def("get_capacities_arcs", &cpp_module::Instance::get_capacities_arcs)
            .def("get_list_of_slopes", &cpp_module::Instance::get_list_of_slopes)
            .def("get_list_of_thresholds", &cpp_module::Instance::get_list_of_thresholds)
            .def("get_parameters", &cpp_module::Instance::get_parameters)
            .def("get_release_times", &cpp_module::Instance::get_release_times)
            .def("get_free_flow_schedule", &cpp_module::Instance::get_free_flow_schedule, py::arg("start_times"));

    py::class_<cpp_module::Scheduler>(m, "cpp_scheduler")
            .def(py::init<cpp_module::Instance &>(),
                 py::arg("cpp_instance"))
            .def("construct_schedule", &cpp_module::Scheduler::construct_schedule)
            .def("construct_solution", &cpp_module::Scheduler::construct_solution,
                 py::arg("start_times"));

    m.def("cppSchedulingLocalSearch", &cpp_module::cppSchedulingLocalSearch,
          py::arg("release_times"),
          py::arg("remaining_time_slack"),
          py::arg("staggering_applied"),
          py::arg("conflicting_sets"),
          py::arg("earliest_departure_times"),
          py::arg("latest_departure_times"),
          py::arg("travel_times_arcs"),
          py::arg("capacities_arcs"),
          py::arg("trip_routes"),
          py::arg("deadlines"),
          py::arg("due_dates"),
          py::arg("list_of_slopes"),
          py::arg("list_of_thresholds"),
          py::arg("parameters"),
          py::arg("lb_travel_time"));
}
