#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>
#include <stdexcept>  // Include for std::out_of_range
#include "solution.h"
#include "tie_manager.h"

namespace cpp_module {

    const double UNUSED_VALUE = -1;
    enum DepartureType {
        TRAVEL, ACTIVATION
    };

    struct Departure {
        double time;
        long arc_id;
        long trip_id;
        long position;
        enum DepartureType event_type;
        long reinsertion_number;
    };

    struct Conflict {
        long arc;
        long current_trip_id;
        long other_trip_id;
        double delay_conflict;
        double distance_to_cover;
        double staggering_current_vehicle;
        double destaggering_other_vehicle;
    };

    struct CompareDepartures {
        bool operator()(Departure const &e1, Departure const &e2) {
            if (std::abs(e1.time - e2.time) > TOLERANCE) {
                return e1.time > e2.time;
            }
            return e1.trip_id < e2.trip_id;
        }
    };

    enum MarkInstruction {
        MARK, NOT_MARK, WAIT
    };


    // Template class for reservable priority queue
    template<typename T, typename Compare>
    class ReservablePriorityQueue : public std::priority_queue<T, std::vector<T>, Compare> {
    public:
        // Reserve memory for the underlying container
        void reserve(size_t capacity) {
            this->c.reserve(capacity);
        }

        // Clear the queue
        void clear() {
            this->c.clear();
        }
    };


    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void;

    class SchedulerFields : public TieManager {


    public:
        using MinQueueDepartures = ReservablePriorityQueue<Departure, CompareDepartures>;
        using MinQueueArrivals = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;

        enum TripStatus {
            INACTIVE, STAGING, ACTIVE
        };


    private:
        MinQueueDepartures pq_departures;
        std::vector<MinQueueArrivals> arrivals_on_arcs;
        std::vector<long> last_processed_position;
        std::vector<long> number_of_reinsertions;
        std::vector<TripID> trips_to_mark;
        bool lazy_update_pq{};
        std::vector<TripStatus> trip_status_list;
        bool break_flow_computation_flag = false;

    protected:


    public:
        explicit SchedulerFields(Instance &arg_instance) : TieManager(arg_instance) {
            trip_status_list = std::vector<TripStatus>(instance.get_number_of_trips(), INACTIVE);
            last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
            clear_and_reserve_pq_departures();
        }

        [[nodiscard]] bool get_break_flow_computation_flag() const {
            return break_flow_computation_flag;
        }


        void set_break_flow_computation_flag(bool arg_flag) {
            break_flow_computation_flag = arg_flag;
        }

        [[nodiscard]] double get_trip_remaining_time_slack(TripID trip_id, Time start_time) const {
            return instance.get_trip_arc_latest_departure_time(trip_id, 0) - start_time;
        }

        [[nodiscard]] double get_trip_staggering_applied(TripID trip_id, Time start_time) const {
            return start_time - instance.get_trip_release_time(trip_id);
        }


    protected:


        [[nodiscard]]   MinQueueArrivals &get_arrivals_on_arc(ArcID arc_id) {
            return arrivals_on_arcs[arc_id];
        }


        void insert_departure_in_arc_arrivals(ArcID arc_id, Departure &arg_departure) {
            arrivals_on_arcs[arc_id].push(arg_departure);
        }

        void initialize_status_vehicles() {
            trip_status_list = std::vector<TripStatus>(instance.get_number_of_trips(), INACTIVE);
            number_of_reinsertions = std::vector<long>(instance.get_number_of_trips(), 0);
            last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
        }

        void insert_trip_to_mark(TripID trip_id) {
            trips_to_mark.push_back(trip_id);
        }

        [[nodiscard]] std::vector<TripID> get_trips_to_mark() const {
            return trips_to_mark;
        }


        void insert_departure_in_pq(const Departure &arg_departure) {
            pq_departures.push(arg_departure);
        }

        Departure get_and_pop_departure_from_pq() {
            auto arg_departure = pq_departures.top();
            pq_departures.pop();
            return arg_departure;
        }


        void clear_vehicles_to_mark() {
            trips_to_mark.clear();
        }

        bool is_pq_empty() {
            return pq_departures.empty();
        }

        // Helper function to clear and reserve a vector
        template<typename T>
        void clear_and_reserve(T &vec, std::size_t size) {
            vec.clear();
            vec.reserve(size);
        }

        // Clear and reserve necessary vectors
        void clear_and_reserve_pq_departures() {
            clear_and_reserve(pq_departures, instance.get_number_of_trips());
        }

        void clear_arrivals_on_arcs() {
            arrivals_on_arcs = std::vector<MinQueueArrivals>(instance.get_number_of_arcs());
        }

        void set_lazy_update_pq_flag(bool arg_flag) {
            lazy_update_pq = arg_flag;
        }


        [[nodiscard]]bool get_lazy_update_pq_flag() const {
            return lazy_update_pq;
        }

        void set_trip_status(TripID trip_id, TripStatus arg_trip_status) {
            trip_status_list[trip_id] = arg_trip_status;
        }

        [[nodiscard]] Position get_trip_last_processed_position(TripID trip_id) {
            return last_processed_position[trip_id];
        }

        [[nodiscard]] long get_trip_reinsertions(TripID trip_id) {
            return number_of_reinsertions[trip_id];
        }

        void increase_trip_reinsertions(TripID trip_id) {
            number_of_reinsertions[trip_id]++;
        }


        void set_trip_last_processed_position(TripID trip_id, Position position) {
            last_processed_position[trip_id] = position;
        }


        [[nodiscard]] TripStatus get_trip_status(TripID trip_id) {
            return trip_status_list[trip_id];
        }


    };

    class Scheduler : public SchedulerFields {

    public:
        explicit Scheduler(Instance &arg_instance) : SchedulerFields(arg_instance) {}


        void initialize_scheduler_for_update_solution();


        [[nodiscard]] static bool
        check_conflict_with_other_vehicle(long other_trip_id, double other_departure, double other_arrival,
                                          const Departure &departure);


        [[nodiscard]] bool
        check_if_vehicle_is_late(double current_vehicle_new_arrival, const Departure &departure) const;

        [[nodiscard]] bool
        check_if_trips_within_conflicting_set_can_conflict(long other_trip_id, long other_position,
                                                           const Departure &departure);


        void initialize_scheduler(const std::vector<double> &release_times);

        Departure get_next_departure(Solution &complete_solution);

        bool check_if_activation_departure_should_be_skipped(const Departure &departure);

        bool check_if_travel_departure_should_be_skipped(const Departure &departure);

        bool check_if_departure_should_be_skipped(const Departure &departure);

        void activate_staging_vehicle(Departure &departure);

        [[nodiscard]] static bool
        check_if_other_has_conflict_with_current(long other_vehicle, double other_original_departure,
                                                 double current_vehicle_new_arrival,
                                                 const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_had_conflict_with_current(long other_vehicle, double other_original_departure,
                                                 double current_original_departure,
                                                 double current_original_arrival,
                                                 const Departure &departure);

        [[nodiscard]]static bool
        check_if_current_had_conflict_with_other(long other_vehicle, double other_original_departure,
                                                 double current_original_departure,
                                                 double other_original_arrival,
                                                 const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_is_first(long other_vehicle, double other_original_departure,
                                const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_was_first(long other_vehicle, double other_original_departure,
                                 double current_original_departure,
                                 const Departure &departure);


        void initialize_priority_queue(const Conflict &conflict, Solution &solution);


        void set_next_departure_and_push_to_queue(double delay, Departure &departure);


        [[nodiscard]] static bool is_arc_dummy(ArcID arc_id) {
            return arc_id == 0;
        }

        Solution construct_solution(const std::vector<Time> &arg_start_times);

        void solve_arc_ties(ArcID arc_id, Solution &complete_solution);

        void solve_tie(Solution &complete_solution, const Tie &tie);

        void solve_solution_ties(Solution &complete_solution);

        bool enough_slack_to_solve_tie(TripID trip_id, const Solution &solution);

        [[nodiscard]] auto check_if_solution_is_feasible(const Departure &departure) const;

        static double compute_delay_on_arc(const double &vehicles_on_arc, const Instance &arg_instance, long arc);

        Departure get_departure(double arg_time, TripID trip_id, Position arg_position, DepartureType arg_type,
                                int arg_reinsertion_number);

        Time process_vehicle(Solution &initial_solution, Solution &new_solution, Departure &departure);

        void
        move_vehicle_forward(Solution &new_solution, double trip_arrival_time, Departure &departure);

        [[nodiscard]] static bool is_within_tolerance(double time1, double time2);

        [[nodiscard]] static bool
        comes_before(double earlier_time, double later_time, long earlier_trip_id, long later_trip_id);

        [[nodiscard]] static bool
        comes_after(double earlier_time, double later_time, long earlier_trip_id, long later_trip_id);

        double get_flow_on_arc(Solution &initial_solution, Solution &new_solution, const Departure &departure);

        Time process_conflicting_set(Solution &initial_solution, Solution &new_solution, const Departure &departure);

        static MarkInstruction
        check_if_other_should_be_marked(const Solution &initial_solution, long other_trip_id,
                                        long other_position,
                                        bool current_conflicts_with_other, const Departure &departure);

        void mark_trip(long other_trip_id, double other_departure_time, long other_position);

        void
        reset_other_schedule_to_reinsertion_time(Solution &initial_solution, Solution &new_solution,
                                                 long other_vehicle,
                                                 long other_position);

        void reinsert_other_in_queue(Solution &initial_solution, Solution &new_solution, long other_trip_id,
                                     long other_position, double other_departure_time);

        bool check_mark_waiting_trip(Solution &initial_solution, TripID other_trip_id,
                                     double current_new_arrival,
                                     const Departure &departure);

        void mark_waiting_trips(Solution &initial_solution, const Solution &new_solution, double current_new_arrival,
                                const Departure &departure);

        void update_total_delay_solution(Solution &current_solution, Solution &new_solution);

        void apply_staggering_to_solve_conflict(Solution &complete_solution, Conflict &conflict);

        Solution update_existing_congested_schedule(Solution &initial_solution, Conflict &conflict);

        double
        handle_active_vehicle(Solution &initial_solution, Solution &new_solution, TripID other_trip_id,
                              long other_position,
                              double other_departure_time, bool current_conflicts_with_other,
                              const Departure &departure);

        double handle_inactive_vehicle(Solution &initial_solution, TripID other_trip_id, long other_position,
                                       bool current_conflicts_with_other, const Departure &departure);

        double process_conflicting_trip(Solution &initial_solution, Solution &new_solution, const Departure &departure,
                                        TripID other_trip_id, Position other_position);

        double compute_vehicles_on_arc(MinQueueArrivals &arrivals_on_arc, const double &departure_time);
    };

}
