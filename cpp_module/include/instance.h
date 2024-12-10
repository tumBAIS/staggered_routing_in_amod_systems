#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>
#include <stdexcept>  // Include for std::out_of_range

namespace cpp_module {

    // Data types
    using TripID = long;
    using Position = long;
    using Time = double;
    using VehicleSchedule = std::vector<std::vector<double>>;
    using PotentiallyConflictingVehiclesSets = std::vector<std::vector<long>>;


    class Instance {
    public:
        const std::vector<std::vector<long>> trip_routes;
        const std::vector<double> travel_times_arcs;
        const std::vector<long> nominalCapacitiesArcs;
        std::vector<double> deadlines;
        std::vector<double> dueDates;
        std::vector<double> release_times;
        PotentiallyConflictingVehiclesSets conflictingSet;
        std::vector<std::vector<double>> earliestDepartureTimes;
        std::vector<std::vector<double>> latestDepartureTimes;
        std::vector<double> freeFlowTravelTimesVehicles;
        long number_of_trips;
        long numberOfArcs;
        std::vector<double> list_of_slopes;
        std::vector<double> list_of_thresholds;

        double maxTimeOptimization;
        double lb_travel_time;


        Instance(const std::vector<std::vector<long>> &argArcBasedShortestPaths,
                 const std::vector<double> &argNominalTravelTimesArcs,
                 const std::vector<long> &argNominalCapacitiesArcs,
                 const std::vector<double> &arg_list_of_slopes,
                 const std::vector<double> &arg_list_of_thresholds,
                 const std::vector<double> &argParameters,
                 const std::vector<double> &arg_release_times,
                 const double arg_lb_travel_time
        ) :
                deadlines(argArcBasedShortestPaths.size()),
                dueDates(argArcBasedShortestPaths.size()),
                freeFlowTravelTimesVehicles(argArcBasedShortestPaths.size(), 0),
                release_times(arg_release_times),
                trip_routes(argArcBasedShortestPaths),
                travel_times_arcs(argNominalTravelTimesArcs),
                nominalCapacitiesArcs(argNominalCapacitiesArcs),
                conflictingSet(argNominalCapacitiesArcs.size()) {
            number_of_trips = (long) argArcBasedShortestPaths.size();
            numberOfArcs = (long) argNominalTravelTimesArcs.size();
            maxTimeOptimization = argParameters[0];
            list_of_slopes = arg_list_of_slopes;
            list_of_thresholds = arg_list_of_thresholds;
            lb_travel_time = arg_lb_travel_time;

            for (auto i = 0; i < number_of_trips; i++) {
                deadlines[i] = std::numeric_limits<double>::max();
                dueDates[i] = std::numeric_limits<double>::max();
            }
        }

        [[nodiscard]] const std::vector<std::vector<long>> &get_trip_routes() const { return trip_routes; }

        [[nodiscard]]const std::vector<double> &get_travel_times_arcs() const { return travel_times_arcs; }

        [[nodiscard]]const std::vector<long> &get_capacities_arcs() const { return nominalCapacitiesArcs; }

        [[nodiscard]]const std::vector<double> &get_list_of_slopes() const { return list_of_slopes; }

        [[nodiscard]]const std::vector<double> &get_list_of_thresholds() const { return list_of_thresholds; }

        [[nodiscard]] std::vector<double> get_parameters() const { return {maxTimeOptimization}; }

        [[nodiscard]]const std::vector<double> &get_release_times() const { return release_times; }

        VehicleSchedule get_free_flow_schedule(const std::vector<double> &start_times) {
            // Initialize the free flow schedule with start times
            std::vector<std::vector<double>> free_flow_schedule;
            free_flow_schedule.reserve(start_times.size());

            for (double start_time: start_times) {
                free_flow_schedule.push_back({start_time});
            }

            // Compute the free flow schedule for each vehicle
            for (size_t vehicle = 0; vehicle < trip_routes.size(); ++vehicle) {
                const std::vector<long> &path = trip_routes[vehicle];
                for (size_t arc_index = 0; arc_index < path.size() - 1; ++arc_index) {
                    int arc = path[arc_index];
                    double last_departure_time = free_flow_schedule[vehicle].back();
                    double next_departure_time = last_departure_time + travel_times_arcs[arc];
                    free_flow_schedule[vehicle].push_back(next_departure_time);
                }
            }

            return free_flow_schedule;
        }
    };

}