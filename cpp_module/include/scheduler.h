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


    const long ITERATION_TO_PRINT = 3; // Has effect only if printsEvaluationFunction is defined

    struct Departure {
        double time;
        long arc_id;
        long trip_id;
        long position;
        enum {
            TRAVEL, ACTIVATION
        } event_type;
        long reinsertion_number;
    };

    struct CompareDepartures {
        bool operator()(Departure const &e1, Departure const &e2) {
            if (e1.time > e2.time) {
                return e1.time > e2.time;
            } else if (e1.time == e2.time) {
                return e1.arc_id > e2.arc_id;
            }
            return false;
        }
    };

    enum VehicleShouldBeMarked {
        YES, NO, MAYBE
    };


    using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;


    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void;

    class SchedulerFields : public TieManager {
    public:
        using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;
        enum TripStatus {
            INACTIVE, STAGING, ACTIVE
        };
        enum InstructionConflictingSet {
            CONTINUE, EVALUATE, BREAK
        };


    private:
        MinQueueDepartures pq_departures;
        std::vector<MinQueueDepartures> arrivals_on_arcs;
        std::vector<long> last_processed_position;
        std::vector<long> number_of_reinsertions;
        std::vector<TripID> trips_to_mark;
        VehicleSchedule original_schedule;
        VehicleSchedule schedule_to_restore;
        MinQueueDepartures pq_to_restore;
        bool lazy_update_pq{};
        bool tie_found{};
        bool trip_is_late{};
        std::vector<TripStatus> trip_status_list;
        bool slack_is_enough = true;

    protected:


    public:
        explicit SchedulerFields(Instance &arg_instance) : TieManager(arg_instance) {
            trip_status_list = std::vector<TripStatus>(instance.get_number_of_trips(), INACTIVE);
            last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
        }


        [[nodiscard]] double get_trip_remaining_time_slack(TripID trip_id, Time start_time) const {
            return instance.get_trip_arc_latest_departure_time(trip_id, 0) - start_time;
        }

        [[nodiscard]] double get_trip_staggering_applied(TripID trip_id, Time start_time) const {
            return start_time - instance.get_trip_release_time(trip_id);
        }


        [[nodiscard]] bool get_slack_is_enough_flag() const {
            return slack_is_enough;
        }

        void set_slack_is_enough_flag(bool arg_flag) {
            slack_is_enough = arg_flag;
        }


    protected:


        [[nodiscard]]   MinQueueDepartures &get_arrivals_on_arc(ArcID arc_id) {
            return arrivals_on_arcs[arc_id];
        }


        void insert_departure_in_arc_arrivals(ArcID arc_id, Departure &arg_departure) {
            arrivals_on_arcs[arc_id].push(arg_departure);
        }

        void set_original_schedule(const VehicleSchedule &schedule) {
            original_schedule = schedule;
        }

        void initialize_status_vehicles() {
            trip_status_list = std::vector<TripStatus>(instance.get_number_of_trips(), INACTIVE);
            number_of_reinsertions = std::vector<long>(instance.get_number_of_trips(), 0);
            last_processed_position = std::vector<long>(instance.get_number_of_trips(), -1);
        }

        [[nodiscard]]Time get_original_trip_departure_at_position(TripID trip_id, Position position) {
            return original_schedule[trip_id][position];
        }


        [[nodiscard]]Time get_last_original_trip_departure(TripID trip_id) {
            return original_schedule[trip_id].back();
        }

        void insert_trip_to_mark(TripID trip_id) {
            trips_to_mark.push_back(trip_id);
        }

        std::vector<TripID> get_trips_to_mark() {
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


        [[nodiscard]] bool get_tie_found_flag() const {
            return tie_found;
        }

        [[nodiscard]] bool get_trip_is_late_flag() const {
            return trip_is_late;
        }

        void set_tie_found_flag(bool arg_flag) {
            tie_found = arg_flag;
        }

        void set_trip_is_late_flag(bool arg_flag) {
            trip_is_late = arg_flag;
        }

        void clear_vehicles_to_mark() {
            trips_to_mark.clear();
        }

        bool is_pq_empty() {
            return pq_departures.empty();
        }

        void clear_departures_pq() {
            pq_departures = MinQueueDepartures();
        }

        void clear_arrivals_on_arcs() {
            arrivals_on_arcs = std::vector<MinQueueDepartures>(instance.get_number_of_arcs());
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


        auto update_existing_congested_schedule(Solution &complete_solution,
                                                const Conflict &conflict) -> void;

        auto update_total_value_solution(Solution &complete_solution) -> void;

        void initialize_scheduler_for_update_solution(const VehicleSchedule &congested_schedule);


        [[nodiscard]] static bool
        check_conflict_with_other_vehicle(long other_vehicle, double other_departure, double other_arrival,
                                          const Departure &departure);


        void reinsert_other_in_queue(Solution &solution,
                                     long other_trip_id,
                                     long other_position,
                                     double other_departure,
                                     long arc);

        void assert_event_pushed_to_queue_is_correct();


        void update_vehicles_on_arc_of_conflicting_set(Solution &solution, double &vehicles_on_arc,
                                                       const Departure &departure);


        void assert_no_vehicles_departing_before_are_marked(long other_vehicle,
                                                            const VehicleSchedule &congested_schedule);

        void assert_other_is_not_active(long other_vehicle);


        static bool check_conditions_to_mark(bool switch_current_with_other_order, bool vehicles_never_overlapped,
                                             bool current_always_first, bool other_always_overlaps);

        void print_update_greatest_time_analyzed() const;

        void print_departure_pushed_to_queue() const;

        void assert_departure_is_feasible(const VehicleSchedule &congested_schedule);

        void assert_lazy_update_is_necessary(double other_departure) const;

        void assert_no_vehicles_are_late(Solution &complete_solution);

        void assert_vehicles_on_arc_is_correct(double vehicles_on_arc, const VehicleSchedule &congested_schedule);

        void reset_other_schedule_to_reinsertion_time(Solution &solution, long other_vehicle,
                                                      long other_position);

        void assert_analyzing_smallest_departure(VehicleSchedule &congested_schedule);

        void assert_other_starts_after_if_has_to_be_processed_on_this_arc_next(long other_vehicle, long other_position,
                                                                               double other_departure);

//        void assert_combination_status_and_departure_type_is_possible();

        void print_reinsertion_vehicle(const long &arc, const long &vehicle, const double &departure_time) const;

        void print_departure() const;

        void print_lazy_update_priority_queue() const;

        void print_iteration_number() const;

        void print_travel_departure_to_skip();

        [[nodiscard]] bool
        check_if_vehicle_is_late(double current_vehicle_new_arrival, const Departure &departure) const;

        [[nodiscard]] InstructionConflictingSet
        check_if_trips_within_conflicting_set_can_conflict(long other_trip_id, long other_position,
                                                           const Departure &departure) const;

        void print_delay_computed(double delay) const;

        void initialize_scheduler(const std::vector<double> &release_times);

        Departure get_next_departure(Solution &complete_solution);

        void
        add_initial_departure_to_priority_queue(double release_time_vehicle, TripID vehicle);

        bool check_if_activation_departure_should_be_skipped(const Departure &departure);

        bool check_if_travel_departure_should_be_skipped(const Departure &departure);

        bool check_if_departure_should_be_skipped(const Departure &departure);

        void activate_staging_vehicle(Departure &departure);

        [[nodiscard]] static bool
        check_if_other_overlaps_now_with_current(long other_vehicle, double other_original_departure,
                                                 double current_vehicle_new_arrival,
                                                 const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_overlapped_with_current(long other_vehicle, double other_original_departure,
                                               double current_original_departure,
                                               double current_original_arrival,
                                               const Departure &departure);

        [[nodiscard]]static bool
        check_if_current_overlapped_with_other(long other_vehicle, double other_original_departure,
                                               double current_original_departure,
                                               double other_original_arrival,
                                               const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_is_first_in_current_schedule(long other_vehicle, double other_original_departure,
                                                    const Departure &departure);

        [[nodiscard]]static bool
        check_if_other_is_first_in_original_schedule(long other_vehicle, double other_original_departure,
                                                     double current_original_departure,
                                                     const Departure &departure);

        void process_conflicting_set(Solution &complete_solution, double &delay, double &current_vehicle_new_arrival,
                                     double &vehicles_on_arc, const Departure &departure);


        void move_vehicle_forward_in_the_queue(double current_vehicle_new_arrival, Departure &departure);


        void process_vehicle(Solution &complete_solution, Departure &departure);

        void initialize_priority_queue(const Conflict &conflict, Solution &solution);

        void
        update_vehicle_schedule(Solution &solution, double current_new_arrival, const Departure &departure) const;

        void mark_vehicle(long other_vehicle, double other_departure, long other_position,
                          const Departure &departure);

        bool
        check_if_should_mark_given_current_arrival_time(TripID other_trip_id,
                                                        double current_vehicle_new_arrival,
                                                        const Departure &departure);

        VehicleShouldBeMarked check_if_other_should_be_marked(long other_vehicle, long other_position,
                                                              bool current_conflicts_with_other,
                                                              const Departure &departure);

        void
        decide_on_vehicles_maybe_to_mark(const VehicleSchedule &congested_schedule, double current_new_arrival,
                                         const Departure &departure);


        void set_next_departure_and_push_to_queue(double delay, Departure &departure);

        [[nodiscard]] bool
        check_if_other_starts_before_current(TripID other_trip_id, const VehicleSchedule &congestedSchedule,
                                             const Departure &departure) const;


        Solution construct_solution(const std::vector<Time> &arg_start_times);

        void solve_arc_ties(ArcID arc_id, Solution &complete_solution);

        void solve_tie(Solution &complete_solution, const Tie &tie);

        void solve_solution_ties(Solution &complete_solution);


        Solution construct_solution_and_solve_ties(const std::vector<double> &start_times);


        bool enough_slack_to_solve_tie(TripID trip_id, const Solution &solution);

        bool check_if_tie_in_set(const Solution &solution, const Departure &departure);

        bool check_if_solution_is_feasible(const Departure &departure) const;
    };

    auto get_index(const std::vector<long> &v, long k) -> long;

    auto compute_delay_on_arc(const double &vehicles_on_arc, const Instance &instance, long arc) -> double;

    auto _assert_solution_is_correct(Solution &new_solution, Scheduler &scheduler) -> void;

    auto compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc, const double &departure_time) -> double;


}
