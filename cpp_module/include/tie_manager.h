//
// Created by anton on 17/12/2024.
//
#include "random"

#ifndef CPP_MODULE_TIE_MANAGER_H
#define CPP_MODULE_TIE_MANAGER_H

#endif //CPP_MODULE_TIE_MANAGER_H


namespace cpp_module {

    class RandomNumberGenerator {
    public:
        static double generate_random_number() {
            // Static random number generator
            static std::mt19937 rng(0); // Mersenne Twister seeded with a fixed value

            // 50% chance for true (positive), 50% for false (negative)
            static std::bernoulli_distribution coin_flip(0.5);

            return coin_flip(rng) ? CONSTR_TOLERANCE : -CONSTR_TOLERANCE;
        }
    };


    struct Tie {
        long vehicle_one;
        long vehicle_two;
        long position_one;
        long position_two;
        long arc;
    };


    class TieManager : public RandomNumberGenerator {

    protected:
        Instance instance;
        bool tie_solved_flag = false;

    public:
        explicit TieManager(Instance &arg_instance) : RandomNumberGenerator(), instance(arg_instance) {}

        bool check_arc_ties(ArcID arc_id, Solution &complete_solution);

        auto check_if_solution_has_ties(Solution &complete_solution) -> bool;

        static bool check_tie(const Solution &solution, const Tie &tie);

        [[nodiscard]] bool get_tie_solved_flag() const {
            return tie_solved_flag;
        }

        void set_tie_solved_flag(bool arg_flag) {
            tie_solved_flag = arg_flag;
        }

        static void print_tie_solved(const Tie &tie, const Solution &old_solution, const Solution &new_solution);
    };
}
