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
        std::vector<double> start_times;
        double total_delay;
        double lb_travel_time;
        bool is_feasible_flag;
        bool has_ties_flag;

    public:
        // Constructor
        explicit Solution(const std::vector<double> &arg_start_times, const Instance &instance)
                : schedule(arg_start_times.size()),
                  start_times(arg_start_times),
                  total_delay(0.0),
                  lb_travel_time(instance.get_lb_travel_time()),
                  is_feasible_flag(true),
                  has_ties_flag(false) {

            for (TripID trip_id = 0; trip_id < arg_start_times.size(); ++trip_id) {
                schedule[trip_id].resize(instance.get_trip_route(trip_id).size());
            }
        }

        // Getters
        [[nodiscard]] const VehicleSchedule &get_schedule() const {
            return schedule;
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

        [[nodiscard]] const Time &get_trip_arrival(TripID trip_id) const {
            return schedule[trip_id].back();
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

        [[nodiscard]]bool has_ties() const {
            return has_ties_flag;
        }

        [[nodiscard]]bool is_feasible() const {
            return is_feasible_flag;
        }

        [[nodiscard]] VehicleSchedule get_delays_on_arcs(const Instance &instance) const {
            // Initialize delays_on_arcs with the number of trips in the instance
            VehicleSchedule delays_on_arcs(instance.get_number_of_trips());

            // Iterate through each trip
            for (int trip_id = 0; trip_id < instance.get_number_of_trips(); ++trip_id) {
                auto route_size = instance.get_trip_route_size(trip_id);

                // Calculate delays for all arcs in the trip route
                for (int position = 0; position < route_size - 1; ++position) {
                    auto arc = instance.get_arc_at_position_in_trip_route(trip_id, position);
                    double departure_current = get_trip_arc_departure(trip_id, position);
                    double departure_next = get_trip_arc_departure(trip_id, position + 1);
                    double travel_time = instance.get_arc_travel_time(arc);

                    double delay_on_arc = departure_next - departure_current - travel_time;
                    delays_on_arcs[trip_id].push_back(delay_on_arc);
                }

                // Add a dummy arc with zero delay
                delays_on_arcs[trip_id].push_back(0.0);
            }

            return delays_on_arcs;
        }

        void set_total_delay(double arg_total_delay) {
            total_delay = arg_total_delay;
        }

        void set_schedule(const VehicleSchedule &arg_schedule) {
            schedule = arg_schedule;
        }

        void set_trip_arc_departure_time(TripID trip_id, Position position, Time time) {
            schedule[trip_id][position] = time;
        }

        void set_feasible_flag(bool arg_flag) {
            is_feasible_flag = arg_flag;
        }

        void set_ties_flag(bool arg_flag) {
            has_ties_flag = arg_flag;
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
