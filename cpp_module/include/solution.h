#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>
#include <stdexcept>  // Include for std::out_of_range
#include "instance.h"

namespace cpp_module {


    class Solution {
    public:
        VehicleSchedule schedule;
        VehicleSchedule delays_on_arcs;
        std::vector<double> start_times;
        std::vector<double> remaining_time_slack;
        std::vector<double> staggering_applied;
        double total_delay;
        double lb_travel_time;
        bool is_feasible_and_improving;
        bool has_ties;

        explicit Solution(const std::vector<double> &arg_start_times, Instance &instance)
                : schedule(arg_start_times.size()), staggering_applied(arg_start_times.size()),
                  delays_on_arcs(arg_start_times.size()),
                  remaining_time_slack(arg_start_times.size()) {
            start_times = arg_start_times;
            total_delay = 0;
            lb_travel_time = instance.lb_travel_time;
            is_feasible_and_improving = true;
            has_ties = false;
            for (auto vehicle = 0; vehicle < size(arg_start_times); vehicle++) {
                schedule[vehicle].resize(instance.trip_routes[vehicle].size());
                delays_on_arcs[vehicle] = delays_on_arcs[vehicle] = std::vector<double>(
                        instance.trip_routes[vehicle].size(), 0.0);
                staggering_applied[vehicle] = 0.0;
                remaining_time_slack[vehicle] = std::numeric_limits<double>::max();
            }
        };

        // Method to get the trip schedule for a given trip_id
        [[nodiscard]] const std::vector<double> &get_trip_schedule(int trip_id) const {
            if (trip_id < 0 || trip_id >= schedule.size()) {
                throw std::out_of_range("Trip ID is out of range.");
            }
            return schedule[trip_id];
        }


        [[nodiscard]] const VehicleSchedule &get_schedule() const {
            return schedule;
        }

        [[nodiscard]] const VehicleSchedule &get_delays_on_arcs() const {
            return delays_on_arcs;
        }

        [[nodiscard]] const std::vector<double> &get_start_times() const {
            return start_times;
        }

        [[nodiscard]] const double &get_total_delay() const {
            return total_delay;
        }

        [[nodiscard]] double get_total_travel_time() const {
            double total_travel_time =
                    total_delay + lb_travel_time; // Assuming total_delay and lb_travel_time are accessible
            return total_travel_time;
        }

        void set_delay_on_arc(double delay, int trip_id, int position) {
            delays_on_arcs[trip_id][position] = delay;
        }
    };

}

