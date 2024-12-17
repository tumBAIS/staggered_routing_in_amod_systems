#include "scheduler.h"
#include "chrono"

#ifndef CPP_MODULE_LOCAL_SEARCH_H
#define CPP_MODULE_LOCAL_SEARCH_H

#endif //CPP_MODULE_LOCAL_SEARCH_H


namespace cpp_module {

    class LocalSearch {

    private:
        Scheduler scheduler;
        struct VehicleInfo {
            long trip_id;
            double departure_time;
            double arrival_time;
            double earliest_departure_time;
            double earliest_arrival_time;
            double latest_departure_time;
            double latest_arrival_time;
        };

        struct ConflictingArrival {
            long vehicle;
            double arrival;
        };

        enum class InstructionsConflict {
            CONTINUE,
            ADD_CONFLICT,
            BREAK
        };

        const Instance &instance;
        VehicleInfo current_vehicle_info{};
        VehicleInfo other_info{};
        ConflictingArrival conflicting_arrival{};
        std::vector<ConflictingArrival> conflicting_arrivals;
        double start_search_clock;


        static bool compare_conflicting_arrivals(const ConflictingArrival &a, const ConflictingArrival &b) {
            return a.arrival < b.arrival;
        }

        std::vector<Conflict> get_conflict_list(const VehicleSchedule &congested_schedule);

        bool check_vehicle_has_delay(const VehicleSchedule &congested_schedule, long current_vehicle);

        void
        update_current_vehicle_info(long current_vehicle, const VehicleSchedule &congested_schedule, long position);

        void add_conflicts_to_conflict_list(std::vector<Conflict> &conflicts_list, long arc);

        InstructionsConflict get_instructions_conflict(const VehicleSchedule &congested_schedule, long other_position);

        Conflict create_conflict(long arc, double delay, ConflictingArrival &sorted_arrival) const;


        [[nodiscard]] double get_start_search_clock() const {
            return start_search_clock;
        }

        static auto get_current_time_in_seconds() -> double {
            using Clock = std::chrono::high_resolution_clock;
            auto now = Clock::now();
            auto epoch = now.time_since_epoch();
            return std::chrono::duration<double>(epoch).count();
        }


    public:

        explicit LocalSearch(Instance &arg_instance) : scheduler(arg_instance),
                                                       instance(arg_instance),
                                                       start_search_clock(get_current_time_in_seconds()) {}


        void reset_new_solution(const Solution &current_solution, Solution &new_solution, Conflict &conflict);

        void apply_staggering_to_solve_conflict(Solution &complete_solution, Conflict &conflict);

        void
        update_current_solution(Solution &current_solution, const Solution &new_solution, Conflict &conflict);

        static void print_move(const Solution &old_solution, const Solution &new_solution, const Conflict &conflict);


        static auto
        check_if_possible_to_solve_conflict(const double &distance_to_cover, const double &slack_vehicle_one,
                                            const double &staggering_applied_vehicle_two);

        void update_distance_to_cover(const Solution &complete_solution, Conflict &conflict);

        bool check_if_solution_is_admissible(Solution &complete_solution);

        auto solve_conflict(Conflict &conflict, Solution &new_solution);

        bool improve_solution(const std::vector<Conflict> &conflicts_list, Solution &current_solution);

        Solution
        get_initial_solution(const std::vector<double> &arg_release_times,
                             const std::vector<double> &arg_remaining_time_slack,
                             const std::vector<double> &arg_staggering_applied);

        auto compute_staggering_applied(const std::vector<Time> &arg_start_times);

        Solution run(std::vector<Time> &arg_start_times);

        auto compute_remaining_time_slack(const std::vector<Time> &arg_start_times);
    };


}
