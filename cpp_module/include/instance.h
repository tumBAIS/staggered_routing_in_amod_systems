#include <utility>
#include <vector>
#include <limits>
#include <stdexcept> // For std::out_of_range

namespace cpp_module {

// Data types
    using TripID = long;
    using ArcID = long;
    using Position = long;
    using Time = double;
    using VehicleSchedule = std::vector<std::vector<Time>>;
    using ConflictingSet = std::vector<TripID>;
    using ConflictingSets = std::vector<ConflictingSet>;
    using TripRoute = std::vector<ArcID>;
// Parameters
    const double CONSTR_TOLERANCE = 1e-3;
    const double TOLERANCE = 1e-6;

    struct Conflict {
        long arc;
        long current_trip_id;
        long other_trip_id;
        double delay_conflict;
        double distance_to_cover;
        double staggering_current_vehicle;
        double destaggering_other_vehicle;
    };


    class Instance {
    private:
        // Attributes
        const std::vector<std::vector<TripID>> trip_routes;
        const std::vector<Time> travel_times_arcs;
        const std::vector<long> nominal_capacities_arcs;
        std::vector<Time> deadlines;
        std::vector<Time> release_times;
        ConflictingSets conflicting_sets;
        std::vector<std::vector<Time>> earliest_departure_times;
        std::vector<std::vector<Time>> latest_departure_times;
        std::vector<Time> free_flow_travel_times_trips;
        long number_of_trips;
        long number_of_arcs;
        std::vector<double> list_of_slopes;
        std::vector<double> list_of_thresholds;
        double max_time_optimization;
        double lb_travel_time;

    public:
        // Constructor
        Instance(
                const std::vector<std::vector<TripID>> &arg_arc_based_shortest_paths,
                const std::vector<Time> &arg_nominal_travel_times_arcs,
                const std::vector<long> &arg_nominal_capacities_arcs,
                const std::vector<double> &arg_list_of_slopes,
                const std::vector<double> &arg_list_of_thresholds,
                const std::vector<double> &arg_parameters,
                const std::vector<Time> &arg_release_times,
                const std::vector<Time> &arg_deadlines,
                ConflictingSets arg_conflicting_sets,
                double arg_lb_travel_time
        )
                : trip_routes(arg_arc_based_shortest_paths),
                  travel_times_arcs(arg_nominal_travel_times_arcs),
                  nominal_capacities_arcs(arg_nominal_capacities_arcs),
                  conflicting_sets(std::move(arg_conflicting_sets)),
                  release_times(arg_release_times),
                  deadlines(arg_deadlines),
                  free_flow_travel_times_trips(arg_arc_based_shortest_paths.size(), 0),
                  list_of_slopes(arg_list_of_slopes),
                  list_of_thresholds(arg_list_of_thresholds),
                  number_of_trips(static_cast<long>(arg_arc_based_shortest_paths.size())),
                  number_of_arcs(static_cast<long>(arg_nominal_travel_times_arcs.size())),
                  max_time_optimization(arg_parameters[0]),
                  lb_travel_time(arg_lb_travel_time) {

            add_total_free_flow_time_vehicles();
        }

        // Add total free-flow travel time for each vehicle in the instance
        auto add_total_free_flow_time_vehicles() -> void {
            for (long trip_id = 0; trip_id < get_number_of_trips(); ++trip_id) {
                for (auto arc: get_trip_route(trip_id)) {
                    increase_free_flow_travel_time_trip(trip_id, get_arc_travel_time(arc));
                }
            }
        }

        // Getters
        [[nodiscard]] const std::vector<std::vector<TripID>> &get_trip_routes() const {
            return trip_routes;
        }

        [[nodiscard]] const double &get_lb_travel_time() const {
            return lb_travel_time;
        }

        [[nodiscard]] const TripRoute &get_trip_route(TripID trip_id) const {
            return trip_routes[trip_id];
        }

        [[nodiscard]] size_t get_trip_route_size(TripID trip_id) const {
            return trip_routes[trip_id].size();
        }


        [[nodiscard]] const Time &get_trip_deadline(TripID trip_id) const {
            return deadlines[trip_id];
        }

        [[nodiscard]] const double &get_trip_free_flow_time(TripID trip_id) const {
            return free_flow_travel_times_trips[trip_id];
        }

        [[nodiscard]] const ArcID &get_arc_at_position_in_trip_route(TripID trip_id, Position position) const {
            return trip_routes[trip_id][position];
        }

        [[nodiscard]] const ConflictingSet &get_conflicting_set(ArcID arc_id) const {
            return conflicting_sets[arc_id];
        }

        [[nodiscard]] const double &get_arc_travel_time(ArcID arc_id) const {
            return travel_times_arcs[arc_id];
        }

        [[nodiscard]] const long &get_arc_capacity(ArcID arc_id) const {
            return nominal_capacities_arcs[arc_id];
        }

        [[nodiscard]] const Time &get_trip_arc_earliest_departure_time(TripID trip_id, Position position) const {
            return earliest_departure_times[trip_id][position];
        }

        [[nodiscard]] const Time &get_trip_arc_latest_departure_time(TripID trip_id, Position position) const {
            return latest_departure_times[trip_id][position];
        }

        [[nodiscard]] size_t get_number_of_pieces_delay_function() const {
            return list_of_slopes.size();
        }

        [[nodiscard]] double get_piece_slope(size_t piece_id) const {
            return list_of_slopes[piece_id];
        }

        [[nodiscard]] double get_piece_threshold(size_t piece_id) const {
            return list_of_thresholds[piece_id];
        }

        [[nodiscard]] const std::vector<Time> &get_travel_times_arcs() const {
            return travel_times_arcs;
        }

        [[nodiscard]] const std::vector<long> &get_capacities_arcs() const {
            return nominal_capacities_arcs;
        }

        [[nodiscard]] const std::vector<double> &get_list_of_slopes() const {
            return list_of_slopes;
        }

        [[nodiscard]] const std::vector<double> &get_list_of_thresholds() const {
            return list_of_thresholds;
        }

        [[nodiscard]] std::vector<double> get_parameters() const {
            return {max_time_optimization};
        }

        [[nodiscard]] double get_max_time_optimization() const {
            return max_time_optimization;
        }


        [[nodiscard]] const std::vector<Time> &get_release_times() const {
            return release_times;
        }


        [[nodiscard]] const Time &get_trip_release_time(TripID trip_id) const {
            return release_times[trip_id];
        }

        [[nodiscard]] const long &get_number_of_trips() const {
            return number_of_trips;
        }

        [[nodiscard]] const long &get_number_of_arcs() const {
            return number_of_arcs;
        }

        // Method to compute free flow schedule
        [[nodiscard]] VehicleSchedule get_free_flow_schedule(const std::vector<Time> &start_times) const {
            VehicleSchedule free_flow_schedule(start_times.size());

            // Initialize the free flow schedule with start times
            for (size_t i = 0; i < start_times.size(); ++i) {
                free_flow_schedule[i].push_back(start_times[i]);
            }

            // Compute the free flow schedule for each vehicle
            for (size_t vehicle = 0; vehicle < trip_routes.size(); ++vehicle) {
                const auto &path = trip_routes[vehicle];
                for (size_t arc_index = 0; arc_index < path.size() - 1; ++arc_index) {
                    long arc = path[arc_index];
                    double last_departure_time = free_flow_schedule[vehicle].back();
                    double next_departure_time = last_departure_time + travel_times_arcs[arc];
                    free_flow_schedule[vehicle].push_back(next_departure_time);
                }
            }

            return free_flow_schedule;
        }

        void insert_trip_in_conflicting_set(ArcID arc_id, TripID trip_id) {
            conflicting_sets[arc_id].push_back(trip_id);
        }

        void increase_free_flow_travel_time_trip(TripID trip_id, double amount) {
            free_flow_travel_times_trips[trip_id] += amount;
        }

        // Setter for deadlines
        void set_deadlines(const std::vector<double> &arg_deadlines) {
            deadlines = arg_deadlines;
        }


        // Setter for earliest departure times
        void set_earliest_departure_times(const std::vector<std::vector<double>> &arg_earliest_departure_times) {
            earliest_departure_times = arg_earliest_departure_times;
        }

        // Setter for latest departure times
        void set_latest_departure_times(const std::vector<std::vector<double>> &arg_latest_departure_times) {
            latest_departure_times = arg_latest_departure_times;
        }

    };

} // namespace cpp_module