#include "scheduler.h"
#include "chrono"

#ifndef CPP_MODULE_LOCAL_SEARCH_H
#define CPP_MODULE_LOCAL_SEARCH_H

#endif //CPP_MODULE_LOCAL_SEARCH_H


namespace cpp_module {

    class LocalSearch : public TieManager {

        // Define a comparison struct
        struct CompareConflicts {

            bool operator()(const Conflict &a, const Conflict &b) const {
                // Compare delays with tolerance
                if (std::abs(a.delay - b.delay) > TOLERANCE) {
                    return a.delay < b.delay; // Higher delay comes first
                }

                // If delays are equal within tolerance, compare trip IDs
                return a.trip_id < b.trip_id; // Larger trip ID comes first
            }
        };

        using ConflictsQueue = ReservablePriorityQueue<Conflict, CompareConflicts>;


    private:
        Scheduler scheduler;
        struct TripInfo {
            long trip_id;
            Position position;
            double departure_time;
            double arrival_time;
            double earliest_departure_time;
            double latest_departure_time;
            double latest_arrival_time;
        };

        enum CounterName {
            WORSE_SOLUTIONS, SLACK_NOT_ENOUGH, SOLUTION_WITH_TIES, ITERATION, INFEASIBLE_SOLUTIONS
        };

        struct Counters {
            long worse_solutions = 0;
            long infeasible_solutions = 0;
            long slack_not_enough = 0;
            long solution_with_ties = 0;
            long iteration = 0;
        };


        enum class InstructionsConflict {
            CONTINUE,
            ADD_CONFLICT,
            BREAK
        };

        const Instance &instance;
        double start_algo_global_clock; // When LS is created
        Counters counters;
        bool improvement_found_flag = false;
        bool verbose = true;

        [[nodiscard]] bool get_improvement_is_found() const {
            return improvement_found_flag;
        }

        void set_improvement_is_found(bool arg_flag) {
            improvement_found_flag = arg_flag;
        }


        static auto get_current_time_in_seconds() -> double {
            using Clock = std::chrono::high_resolution_clock;
            auto now = Clock::now();
            auto epoch = now.time_since_epoch();
            return std::chrono::duration<double>(epoch).count();
        }


        void increase_counter(CounterName counter_name) {
            switch (counter_name) {
                case SLACK_NOT_ENOUGH:
                    counters.slack_not_enough++;
                case SOLUTION_WITH_TIES:
                    counters.solution_with_ties++;
                case INFEASIBLE_SOLUTIONS:
                    counters.infeasible_solutions++;
                case WORSE_SOLUTIONS:
                    counters.worse_solutions++;
                case ITERATION:
                    counters.iteration++;
            }
        }

        [[nodiscard]] int get_counter(CounterName counter_name) const {
            switch (counter_name) {
                case SLACK_NOT_ENOUGH:
                    return counters.slack_not_enough;
                case SOLUTION_WITH_TIES:
                    return counters.solution_with_ties;
                case INFEASIBLE_SOLUTIONS:
                    return counters.infeasible_solutions;
                case WORSE_SOLUTIONS:
                    return counters.worse_solutions;
                case ITERATION:
                    return counters.iteration;
            }
        }

        void reset_counters() {
            counters = Counters();
        }


    public:

        explicit LocalSearch(Instance &arg_instance, bool arg_verbose = true) : TieManager(arg_instance),
                                                                                scheduler(arg_instance),
                                                                                instance(arg_instance),
                                                                                start_algo_global_clock(
                                                                                        get_current_time_in_seconds()),
                                                                                verbose(arg_verbose) {}


        auto solve_conflict(Conflict &conflict, Solution &initial_solution) -> Solution;


        Solution run(std::vector<Time> &arg_start_times);

        static void print_initial_delay(const Solution &arg_solution);

        static auto print_infeasible_message() -> void;

        bool check_if_time_limit_is_reached();

        bool check_vehicle_has_delay(const Solution &solution, long trip_id);

        ConflictsQueue get_conflicts_queue(const Solution &solution);

        TripInfo get_trip_info_struct(long current_trip, const Solution &solution, long position);

        static InstructionsConflict get_instructions_conflict(const TripInfo &trip_info, const TripInfo &other_info);

        static Conflict
        create_conflict(long arc, double delay, const TripInfo &trip_info, const TripInfo &other_trip_info);


        std::vector<Conflict>
        find_conflicts_on_arc(long arc, double arc_delay, const Solution &solution, const TripInfo &trip_info,
                              const std::vector<long> &conflicting_set);

        bool check_if_possible_to_solve_conflict(const Conflict &conflict, const Solution &solution);

        Solution improve_solution(ConflictsQueue &conflicts_queue, Solution &best_known_solution);

        void
        print_move(const Solution &best_known_solution, const Solution &new_solution, const Conflict &conflict);

        void print_search_statistics();

        void print_search_statistics(double start_algo_global_clock);
    };


}
