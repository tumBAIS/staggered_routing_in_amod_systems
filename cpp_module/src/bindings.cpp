#include <algorithm>
#include <iostream>
#include <cmath>
#include <queue>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "local_search.h"

namespace cpp_module {

// Construct a solution based on the start times
    auto Scheduler::construct_solution(const std::vector<double> &start_times) -> Solution {
        Solution complete_solution(start_times, instance);
        construct_schedule(complete_solution);
        check_if_solution_has_ties(instance, complete_solution);
        if (complete_solution.get_ties_flag()) {
            solve_solution_ties(instance, complete_solution, *this);
        }
        return complete_solution;
    }


// Generate an initial solution for local search
    auto get_initial_solution_for_local_search(
            Scheduler &scheduler,
            Instance &instance,
            const std::vector<double> &arg_release_times,
            const std::vector<double> &arg_remaining_time_slack,
            const std::vector<double> &arg_staggering_applied
    ) -> Solution {
        Solution current_solution(arg_release_times, instance);
        scheduler.construct_schedule(current_solution);

        if (!current_solution.get_feasible_and_improving_flag()) {
            std::cout << "Initial solution is infeasible - local search stopped\n";
            return current_solution;
        }

        current_solution.set_remaining_time_slack(arg_remaining_time_slack);
        current_solution.set_staggering_applied(arg_staggering_applied);

        return current_solution;
    }

// Perform local search
    auto cpp_local_search(
            const std::vector<double> &arg_release_times,
            const std::vector<double> &arg_remaining_time_slack,
            const std::vector<double> &arg_staggering_applied,
            Instance &arg_instance) -> VehicleSchedule {

        Scheduler scheduler(arg_instance);
        Solution current_solution = get_initial_solution_for_local_search(
                scheduler,
                arg_instance,
                arg_release_times,
                arg_remaining_time_slack,
                arg_staggering_applied
        );

        std::cout << "Local search received a solution with " << std::round(current_solution.get_total_delay())
                  << " sec of delay\n";

        if (!current_solution.get_feasible_and_improving_flag()) {
            return current_solution.get_schedule();
        }

        check_if_solution_has_ties(arg_instance, current_solution);

        if (current_solution.get_ties_flag()) {
            solve_solution_ties(arg_instance, current_solution, scheduler);
        }
        auto improved_solution = LocalSearch(arg_instance).run(current_solution);

        return current_solution.get_schedule();
    }

} // namespace cpp_module

namespace py = pybind11;

PYBIND11_MODULE(cpp_module, m) {
    m.doc() = "CPP module";

    // Solution class bindings
    py::class_<cpp_module::Solution>(m, "cpp_solution")
            .def(py::init<const std::vector<double> &, cpp_module::Instance &>(),
                 py::arg("start_times"),
                 py::arg("cpp_instance"))
            .def("get_trip_schedule", &cpp_module::Solution::get_trip_schedule, py::arg("trip_id"))
            .def("get_schedule", &cpp_module::Solution::get_schedule)
            .def("get_start_times", &cpp_module::Solution::get_start_times)
            .def("get_trip_start_time", &cpp_module::Solution::get_trip_start_time)
            .def("get_delays_on_arcs", &cpp_module::Solution::get_delays_on_arcs)
            .def("get_total_delay", &cpp_module::Solution::get_total_delay)
            .def("get_total_travel_time", &cpp_module::Solution::get_total_travel_time);

    // Instance class bindings
    py::class_<cpp_module::Instance>(m, "cpp_instance")
            .def(py::init<const std::vector<std::vector<long>> &,
                         const std::vector<double> &,
                         const std::vector<long> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const std::vector<double> &,
                         const cpp_module::ConflictingSets &,
                         const cpp_module::VehicleSchedule &,
                         const cpp_module::VehicleSchedule &,
                         const double &>(),
                 py::arg("set_of_vehicle_paths"),
                 py::arg("travel_times_arcs"),
                 py::arg("capacities_arcs"),
                 py::arg("list_of_slopes"),
                 py::arg("list_of_thresholds"),
                 py::arg("parameters"),
                 py::arg("release_times"),
                 py::arg("deadlines"),
                 py::arg("conflicting_sets"),
                 py::arg("earliest_departures"),
                 py::arg("latest_departures"),
                 py::arg("lb_travel_time"))
            .def("get_trip_routes", &cpp_module::Instance::get_trip_routes)
            .def("get_travel_times_arcs", &cpp_module::Instance::get_travel_times_arcs)
            .def("get_capacities_arcs", &cpp_module::Instance::get_capacities_arcs)
            .def("get_list_of_slopes", &cpp_module::Instance::get_list_of_slopes)
            .def("get_list_of_thresholds", &cpp_module::Instance::get_list_of_thresholds)
            .def("get_parameters", &cpp_module::Instance::get_parameters)
            .def("get_release_times", &cpp_module::Instance::get_release_times)
            .def("get_trip_release_time", &cpp_module::Instance::get_trip_release_time)
            .def("get_free_flow_schedule", &cpp_module::Instance::get_free_flow_schedule, py::arg("start_times"));

    // Scheduler class bindings
    py::class_<cpp_module::Scheduler>(m, "cpp_scheduler")
            .def(py::init<cpp_module::Instance &>(), py::arg("cpp_instance"))
            .def("construct_schedule", &cpp_module::Scheduler::construct_schedule)
            .def("construct_solution", &cpp_module::Scheduler::construct_solution, py::arg("start_times"));

    // Function binding for local search
    m.def("cpp_local_search", &cpp_module::cpp_local_search,
          py::arg("release_times"),
          py::arg("remaining_time_slack"),
          py::arg("staggering_applied"),
          py::arg("cpp_instance"));
}
