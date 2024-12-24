//
// Created by anton on 17/12/2024.
//


#ifndef CPP_MODULE_TIE_MANAGER_H
#define CPP_MODULE_TIE_MANAGER_H

#endif //CPP_MODULE_TIE_MANAGER_H


namespace cpp_module {


    struct Tie {
        long vehicle_one;
        long vehicle_two;
        long position_one;
        long position_two;
        long arc;
    };


    class TieManager {

    protected:
        Instance instance;

    public:
        explicit TieManager(Instance &arg_instance) : instance(arg_instance) {}


        bool check_arc_ties(ArcID arc_id, Solution &complete_solution);

        auto check_if_solution_has_ties(Solution &complete_solution) -> bool;

        static void print_tie_solved(const Tie &tie);

        static bool check_tie(const Solution &solution, const Tie &tie);

    };
}
