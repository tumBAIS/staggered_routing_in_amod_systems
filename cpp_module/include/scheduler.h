#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>
#include <stdexcept>  // Include for std::out_of_range
#include "solution.h"

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

    struct Tie {
        long vehicle_one;
        long vehicle_two;
        long position_one;
        long position_two;
        long arc;
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

    using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;

    auto cpp_local_search(const std::vector<double> &arg_release_times,
                          const std::vector<double> &arg_remaining_time_slack,
                          const std::vector<double> &arg_staggering_applied,
                          const ConflictingSetsList &arg_conflicting_sets,
                          const std::vector<std::vector<double>> &earliest_departure_times,
                          const std::vector<std::vector<double>> &latest_departure_times,
                          const std::vector<double> &arg_nominal_travel_times_arcs,
                          const std::vector<long> &arg_nominal_capacities_arcs_utilized,
                          const std::vector<std::vector<long>> &arc_based_shortest_paths,
                          const std::vector<double> &arg_deadlines,
                          const std::vector<double> &arg_list_of_slopes,
                          const std::vector<double> &arg_list_of_thresholds,
                          const std::vector<double> &arg_parameters,
                          const double &lb_travel_time) -> VehicleSchedule;

    auto sort_conflicts(std::vector<Conflict> &conflicts_in_schedule) -> void;

    class Scheduler {
        using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;
    public:
        MinQueueDepartures pq_departures;
        std::vector<MinQueueDepartures> arrivals_on_arcs;
        std::vector<long> last_processed_position;
        std::vector<long> number_of_reinsertions;
        std::vector<long> vehicles_to_mark;
        Departure departure{};
        Departure other_trip_departure{};
        Instance &instance;
        double best_total_delay;
        VehicleSchedule original_schedule;
        VehicleSchedule schedule_to_restore;
        MinQueueDepartures pq_to_restore;
        bool lazy_update_pq{};
        bool tie_found{};
        bool trip_is_late{};
        enum VehicleStatusType {
            INACTIVE, STAGING, ACTIVE
        };
        enum VehicleShouldBeMarked {
            YES, NO, MAYBE
        };

        enum InstructionConflictingSet {
            CONTINUE, EVALUATE, BREAK
        };
        double start_search_clock;
        std::vector<VehicleStatusType> trip_status_list;
        long iteration;
        long worse_solutions = 0;
        long slack_not_enough = 0;
        long solution_with_ties = 0;
        long explored_solutions = 0;
        bool slack_is_enough = true;

        explicit Scheduler(Instance &arg_instance) :
                instance(arg_instance) {
            start_search_clock = clock() / (double) CLOCKS_PER_SEC;
            best_total_delay = std::numeric_limits<double>::max();
            trip_status_list = std::vector<VehicleStatusType>(instance.get_number_of_trips(),
                                                              VehicleStatusType::INACTIVE);
            iteration = 0;
        };

        auto construct_schedule(Solution &complete_solution) -> void;

        auto update_existing_congested_schedule(Solution &complete_solution,
                                                const Conflict &conflict) -> void;

        auto update_total_value_solution(Solution &complete_solution) -> void;

        void initialize_scheduler_for_update_solution(const VehicleSchedule &congested_schedule);

        void initialize_priority_queue(const Conflict &conflict, Solution &solution);

        auto check_if_other_should_be_marked(long other_vehicle, long other_position,
                                             bool current_conflicts_with_other) -> VehicleShouldBeMarked;

        [[nodiscard]] bool
        check_conflict_with_other_vehicle(long other_vehicle, double other_departure, double other_arrival) const;

        bool check_if_should_mark_given_current_arrival_time(TripID other_trip_id,
                                                             double current_vehicle_new_arrival);

        void mark_vehicle(long other_vehicle, double other_departure, long other_position);

        void move_vehicle_forward_in_the_queue(double current_vehicle_new_arrival);

        [[nodiscard]] bool
        check_if_other_starts_before_current(TripID other_trip_id,
                                             const VehicleSchedule &congested_schedule) const;

        bool check_if_departure_should_be_skipped();

        auto check_if_activation_departure_should_be_skipped() -> bool;

        auto check_if_travel_departure_should_be_skipped() -> bool;

        void update_vehicle_schedule(Solution &solution, double current_new_arrival) const;

        void activate_staging_vehicle();

        void reinsert_other_in_queue(Solution &solution,
                                     long other_vehicle,
                                     long other_position,
                                     double other_departure,
                                     long arc);

        void assert_event_pushed_to_queue_is_correct();

        void add_departure_to_priority_queue(double release_time_vehicle, TripID vehicle);

        void update_vehicles_on_arc_of_conflicting_set(Solution &solution, double &vehicles_on_arc);

        void decide_on_vehicles_maybe_to_mark(const VehicleSchedule &congested_schedule, double current_new_arrival);

        void assert_no_vehicles_departing_before_are_marked(long other_vehicle,
                                                            const VehicleSchedule &congested_schedule);

        void initialize_status_vehicles();

        void process_conflicting_set(Solution &complete_solution,
                                     double &delay,
                                     double &current_vehicle_new_arrival,
                                     double &vehicles_on_arc);

        void process_vehicle(Solution &complete_solution);

        void assert_other_is_not_active(long other_vehicle);

        [[nodiscard]] bool
        check_if_other_is_first_in_original_schedule(long other_vehicle, double other_original_departure,
                                                     double current_original_departure) const;

        [[nodiscard]] bool
        check_if_other_is_first_in_current_schedule(long other_vehicle, double other_original_departure) const;

        [[nodiscard]] bool check_if_current_overlapped_with_other(long other_vehicle,
                                                                  double other_original_departure,
                                                                  double current_original_departure,
                                                                  double other_original_arrival) const;

        [[nodiscard]] bool check_if_other_overlapped_with_current(long other_vehicle, double other_original_departure,
                                                                  double current_original_departure,
                                                                  double current_original_arrival) const;

        [[nodiscard]] bool check_if_other_overlaps_now_with_current(long other_vehicle, double other_original_departure,
                                                                    double current_vehicle_new_arrival) const;

        static bool check_conditions_to_mark(bool switch_current_with_other_order, bool vehicles_never_overlapped,
                                             bool current_always_first, bool other_always_overlaps);

        void print_update_greatest_time_analyzed() const;

        void print_departure_pushed_to_queue() const;

        bool check_if_tie_in_set(const VehicleSchedule &congested_schedule);

        void assert_departure_is_feasible(const VehicleSchedule &congested_schedule);

        void assert_lazy_update_is_necessary(double other_departure) const;

        void assert_no_vehicles_are_late(Solution &complete_solution);

        void assert_vehicles_on_arc_is_correct(double vehicles_on_arc, const VehicleSchedule &congested_schedule);

        void reset_other_schedule_to_reinsertion_time(Solution &solution, long other_vehicle,
                                                      long other_position);

        void assert_analyzing_smallest_departure(VehicleSchedule &congested_schedule);

        void assert_other_starts_after_if_has_to_be_processed_on_this_arc_next(long other_vehicle, long other_position,
                                                                               double other_departure);

        void assert_combination_status_and_departure_type_is_possible();

        void print_reinsertion_vehicle(const long &arc, const long &vehicle, const double &departure_time) const;

        void print_departure() const;

        void print_lazy_update_priority_queue() const;

        void print_iteration_number() const;

        void print_travel_departure_to_skip();

        [[nodiscard]] bool check_if_vehicle_is_late(double current_vehicle_new_arrival) const;

        [[nodiscard]] InstructionConflictingSet
        check_if_trips_within_conflicting_set_can_conflict(long other_trip_id, long other_position) const;

        void print_delay_computed(double delay) const;

        Solution construct_solution(const std::vector<double> &start_times);

        [[nodiscard]] bool check_if_solution_is_admissible(double total_delay) const;

        void set_next_departure_and_push_to_queue(double delay);

        void initialize_scheduler(const std::vector<double> &release_times);

        void get_next_departure(Solution &complete_solution);
    };

    auto apply_staggering_to_solve_conflict(Solution &complete_solution,
                                            Conflict &conflict) -> void;

    static auto reset_new_solution(const Solution &current_solution, Solution &new_solution,
                                   Conflict &conflict) -> void;

    static auto update_current_solution(Solution &current_solution,
                                        const Solution &new_solution,
                                        Conflict &conflict) -> void;

    auto get_index(const std::vector<long> &v, long k) -> long;

    auto stagger_trip(Solution &complete_solution, long vehicle, double staggering) -> void;

    auto solve_solution_ties(const Instance &instance, Solution &complete_solution, Scheduler &scheduler) -> void;

    auto check_if_solution_has_ties(const Instance &instance, Solution &complete_solution) -> void;

    auto compute_delay_on_arc(const double &vehicles_on_arc, const Instance &instance, long arc) -> double;

    auto _assert_solution_is_correct(Solution &new_solution, Scheduler &scheduler) -> void;

    auto improve_towards_solution_quality(const Instance &instance, Solution &current_solution,
                                          Scheduler &scheduler) -> void;

    auto compute_vehicles_on_arc(MinQueueDepartures &arrivals_on_arc, const double &departure_time) -> double;

    auto check_if_vehicles_have_tie(const VehicleSchedule &congested_schedule, const Tie &tie) -> bool;

    auto initialize_conflicting_sets_for_construct_schedule(Instance &instance) -> void;
}
