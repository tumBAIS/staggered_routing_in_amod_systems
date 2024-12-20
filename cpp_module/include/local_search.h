#include "scheduler.h"
#include "chrono"

#ifndef CPP_MODULE_LOCAL_SEARCH_H
#define CPP_MODULE_LOCAL_SEARCH_H

#endif //CPP_MODULE_LOCAL_SEARCH_H


namespace cpp_module {

    class LocalSearch : public TieManager {

    private:
        Scheduler scheduler;
        struct TripInfo {
            long trip_id;
            double departure_time;
            double arrival_time;
            double earliest_departure_time;
            double latest_departure_time;
            double latest_arrival_time;
        };

        enum CounterName {
            WORSE_SOLUTIONS, SLACK_NOT_ENOUGH, SOLUTION_WITH_TIES, EXPLORED_SOLUTIONS, ITERATION
        };

        struct Counters {
            long worse_solutions = 0;
            long slack_not_enough = 0;
            long solution_with_ties = 0;
            long explored_solutions = 0;
            long iteration = 0;
        };

        enum class InstructionsConflict {
            CONTINUE,
            ADD_CONFLICT,
            BREAK
        };

        const Instance &instance;
        double start_search_clock;
        Counters counters;
        bool improvement_found_flag = false;

        [[nodiscard]] bool get_improvement_is_found() const {
            return improvement_found_flag;
        }

        void set_improvement_is_found(bool arg_flag) {
            improvement_found_flag = arg_flag;
        }

        [[nodiscard]] long get_iteration() const {
            return counters.iteration;
        }


        static auto get_current_time_in_seconds() -> double {
            using Clock = std::chrono::high_resolution_clock;
            auto now = Clock::now();
            auto epoch = now.time_since_epoch();
            return std::chrono::duration<double>(epoch).count();
        }


        void increase_counter(CounterName counter_name) {
            switch (counter_name) {
                case EXPLORED_SOLUTIONS:
                    counters.explored_solutions++;
                case SLACK_NOT_ENOUGH:
                    counters.slack_not_enough++;
                case SOLUTION_WITH_TIES:
                    counters.solution_with_ties++;
                case WORSE_SOLUTIONS:
                    counters.worse_solutions++;
                case ITERATION:
                    counters.iteration++;
            }
        }


    public:

        explicit LocalSearch(Instance &arg_instance) : TieManager(arg_instance),
                                                       scheduler(arg_instance),
                                                       instance(arg_instance),
                                                       start_search_clock(get_current_time_in_seconds()) {}


        static void reset_new_solution(const Solution &current_solution, Solution &new_solution, Conflict &conflict);

        static void
        update_current_solution(Solution &current_solution, const Solution &new_solution, Conflict &conflict);

        static void print_move(const Solution &old_solution, const Solution &new_solution, const Conflict &conflict);

        void update_distance_to_cover(const Solution &complete_solution, Conflict &conflict);

        bool check_if_solution_is_admissible(Solution &complete_solution);

        auto solve_conflict(Conflict &conflict, Solution &initial_solution) -> Solution;

        auto improve_solution(const std::vector<Conflict> &conflicts_list, Solution &current_solution) -> Solution;

        Solution run(std::vector<Time> &arg_start_times);

        static void print_initial_delay(const Solution &arg_solution);

        static auto print_infeasible_message() -> void;

        bool check_if_time_limit_is_reached();

        bool check_vehicle_has_delay(const Solution &solution, long trip_id);

        std::vector<Conflict> get_conflicts_list(const Solution &solution);

        TripInfo get_trip_info_struct(long current_trip, const Solution &solution, long position);

        static InstructionsConflict get_instructions_conflict(const TripInfo &trip_info, const TripInfo &other_info);

        static Conflict
        create_conflict(long arc, double delay, const TripInfo &trip_info, const TripInfo &conflicting_trip_info);


        std::vector<Conflict>
        find_conflicts_on_arc(long arc, double arc_delay, const Solution &solution, const TripInfo &trip_info,
                              const std::vector<long> &conflicting_set);

        bool check_if_possible_to_solve_conflict(const Conflict &conflict, const Solution &solution);
    };


}
