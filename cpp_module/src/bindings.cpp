#include <algorithm>
#include <iostream>
#include <cmath>
#include <queue>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "local_search.h"

namespace cpp_module {

// Construct a solution based on the start times
    auto Scheduler::construct_solution_and_solve_ties(const std::vector<double> &start_times) -> Solution {
        //TODO: remove
        Solution complete_solution = construct_solution(start_times);
        check_if_solution_has_ties(complete_solution);
        if (complete_solution.get_ties_flag()) {
            solve_solution_ties(complete_solution);
        }
        return complete_solution;
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
            .def("construct_solution", &cpp_module::Scheduler::construct_solution_and_solve_ties,
                 py::arg("start_times"));


    // Solution class bindings
    py::class_<cpp_module::LocalSearch>(m, "LocalSearch")
            .def(py::init<cpp_module::Instance &>(),
                 py::arg("instance"))
            .def("run", &cpp_module::LocalSearch::run);
}
