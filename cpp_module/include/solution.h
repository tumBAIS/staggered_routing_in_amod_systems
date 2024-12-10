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
        std::vector<std::vector<bool>> tableWithCapReached;
        std::vector<double> start_times;
        std::vector<double> remainingTimeSlack;
        std::vector<double> staggeringApplied;
        double total_delay;
        double lb_travel_time;
        double totalTardiness;
        double solutionValue;
        bool scheduleIsFeasibleAndImproving;
        bool solutionHasTies;
        bool capReached;
        long timesCapIsReached{};

        explicit Solution(const std::vector<double> &argReleaseTimes, Instance &instance)
                : schedule(argReleaseTimes.size()), staggeringApplied(argReleaseTimes.size()),
                  delays_on_arcs(argReleaseTimes.size()),
                  remainingTimeSlack(argReleaseTimes.size()),
                  tableWithCapReached(argReleaseTimes.size()) {
            start_times = argReleaseTimes;
            total_delay = 0;
            totalTardiness = 0;
            solutionValue = 0;
            lb_travel_time = instance.lb_travel_time;
            scheduleIsFeasibleAndImproving = true;
            solutionHasTies = false;
            capReached = false;
            for (auto vehicle = 0; vehicle < size(argReleaseTimes); vehicle++) {
                schedule[vehicle].resize(instance.trip_routes[vehicle].size());
                delays_on_arcs[vehicle] = delays_on_arcs[vehicle] = std::vector<double>(
                        instance.trip_routes[vehicle].size(), 0.0);
                staggeringApplied[vehicle] = 0.0;
                remainingTimeSlack[vehicle] = std::numeric_limits<double>::max();
                tableWithCapReached[vehicle].resize(instance.trip_routes[vehicle].size());
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

