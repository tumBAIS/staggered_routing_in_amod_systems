#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <stdexcept> // For std::out_of_range
#include "instance.h"

// Define a macro to enable or disable range checks
#define ENABLE_RANGE_CHECKS_SOLUTION
// Print a message during compilation if the macro is defined
#ifdef ENABLE_RANGE_CHECKS_SOLUTION
#pragma message("ENABLE_RANGE_CHECKS_SOLUTION is defined: Range checks will be included in the code.")
#endif


namespace cpp_module {

    class Solution {
    public:
        using VehicleSchedule = std::vector<std::vector<double>>;

    private:
        VehicleSchedule schedule;
        VehicleSchedule delays_on_arcs;
        std::vector<double> start_times;
        double total_delay;
        double lb_travel_time;
        bool is_feasible_flag;
        bool has_ties;

    public:
        // Constructor
        explicit Solution(const std::vector<double> &arg_start_times, const Instance &instance)
                : schedule(arg_start_times.size()),
                  delays_on_arcs(arg_start_times.size()),
                  start_times(arg_start_times),
                  total_delay(0.0),
                  lb_travel_time(instance.get_lb_travel_time()),
                  is_feasible_flag(true),
                  has_ties(false) {

            for (TripID trip_id = 0; trip_id < arg_start_times.size(); ++trip_id) {
                schedule[trip_id].resize(instance.get_trip_route(trip_id).size());
                delays_on_arcs[trip_id] = std::vector<double>(instance.get_trip_route(trip_id).size(), 0.0);
            }
        }

        // Getters
        [[nodiscard]] const VehicleSchedule &get_schedule() const {
            return schedule;
        }

        [[nodiscard]] const VehicleSchedule &get_delays_on_arcs() const {
            return delays_on_arcs;
        }

        [[nodiscard]] const std::vector<double> &get_start_times() const {
            return start_times;
        }

        [[nodiscard]] const Time &get_trip_start_time(TripID trip_id) const {
            return start_times[trip_id];
        }

        [[nodiscard]] const Time &get_trip_arc_departure(TripID trip_id, Position position) const {
            return schedule[trip_id][position];
        }

        [[nodiscard]] double get_total_delay() const {
            return total_delay;
        }

        [[nodiscard]] double get_total_travel_time() const {
            return total_delay + lb_travel_time;
        }

        [[nodiscard]] const std::vector<double> &get_trip_schedule(int trip_id) const {
#ifdef ENABLE_RANGE_CHECKS_SOLUTION
            if (trip_id < 0 || static_cast<size_t>(trip_id) >= schedule.size()) {
                throw std::out_of_range("Trip ID is out of range.");
            }
#endif
            return schedule[trip_id];
        }

        [[nodiscard]]bool get_ties_flag() const {
            return has_ties;
        }

        [[nodiscard]]bool is_feasible() const {
            return is_feasible_flag;
        }

        // Setters
        void set_delay_on_arc(double delay, int trip_id, int position) {
#ifdef ENABLE_RANGE_CHECKS_SOLUTION
            if (trip_id < 0 || static_cast<size_t>(trip_id) >= delays_on_arcs.size()) {
                throw std::out_of_range("Trip ID is out of range.");
            }
            if (position < 0 || static_cast<size_t>(position) >= delays_on_arcs[trip_id].size()) {
                throw std::out_of_range("Position is out of range.");
            }
#endif
            delays_on_arcs[trip_id][position] = delay;
        }

        void set_total_delay(double arg_total_delay) {
            total_delay = arg_total_delay;
        }

        void set_schedule(const VehicleSchedule &arg_schedule) {
            schedule = arg_schedule;
        }

        void set_trip_arc_departure(TripID trip_id, Position position, Time time) {
            schedule[trip_id][position] = time;
        }

        void set_feasible_flag(bool arg_flag) {
            is_feasible_flag = arg_flag;
        }

        void set_ties_flag(bool arg_flag) {
            has_ties = arg_flag;
        }

        // Other methods

        void increase_total_delay(double delay_increase) {
            total_delay += delay_increase;
        }

        void increase_trip_start_time(TripID trip_id, double amount) {
            start_times[trip_id] += amount;
        }

    };


} // namespace cpp_module
