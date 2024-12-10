#include "scheduler.h"
#include <queue>
#include "algorithm"
#include "iostream"

namespace cpp_module {

    auto initializeConflictingSetsForConstructSchedule(Instance &instance) -> void {
        long vehicle = 0;
        for (const auto &path: instance.trip_routes) {
            for (auto arc: path) {
                instance.conflictingSet[arc].push_back(vehicle);
            }
            vehicle++;
        }
    }


    auto getIndex(const std::vector<long> &v, long K) -> long {
        auto it = find(v.begin(), v.end(), K);
        long index;
        // If element was found
        if (it != v.end()) {   // calculating the index
            // of K
            index = it - v.begin();
        } else
            // If the element is not present in the vector
            index = -1;

        return index;
    }


    auto _initializeCompleteSolution(Solution &completeSolution) -> void {
        completeSolution.set_total_delay(0);
        completeSolution.set_feasible_and_improving_flag(true);
        completeSolution.set_ties_flag(false);
    }

    auto
    Scheduler::_initializeScheduler(const std::vector<double> &releaseTimes) -> void {
        // reset priority queues, reset counter cap reached, initialize priority queue departures
        priorityQueueDepartures = MinQueueDepartures();
        arrivalsOnArcs = std::vector<MinQueueDepartures>(instance.numberOfArcs);
        departure = Departure();
        for (auto vehicle = 0; vehicle < instance.number_of_trips; vehicle++) {
            departure.time = releaseTimes[vehicle];
            departure.trip_id = vehicle;
            departure.position = 0;
            departure.arc = instance.trip_routes[departure.trip_id][departure.position];
            priorityQueueDepartures.push(departure);
        }
    }

    auto
    Scheduler::_setNextDepartureOfVehicleAndPushToQueue(const double delay) -> void {
        departure.time = departure.time + instance.travel_times_arcs[departure.arc] + delay;
        arrivalsOnArcs[departure.arc].push(departure);
        if (departure.position + 1 < instance.trip_routes[departure.trip_id].size()) {
            departure.position = (departure.position + 1);
            departure.arc = instance.trip_routes[departure.trip_id][departure.position];
            priorityQueueDepartures.push(departure);
        }
    }

    auto Scheduler::checkIfSolutionIsAdmissible(const double total_delay) -> bool {

        if (departure.time > instance.deadlines[departure.trip_id] + TOLERANCE) {
            std::cout << "Deadline vehicle " << departure.trip_id << " : " << instance.deadlines[departure.trip_id] <<
                      " position :" << departure.position << " len path :"
                      << instance.trip_routes[departure.trip_id].size() <<
                      " time: " << departure.time << "\n";
            return false;
        }
        if (total_delay >= best_total_delay) {
            return false;
        }

        return true;
    }

    auto Scheduler::_getNextDeparture(Solution &completeSolution) -> void {
        departure = priorityQueueDepartures.top();
        priorityQueueDepartures.pop();
        completeSolution.set_trip_arc_departure(departure.trip_id, departure.position, departure.time);
    }


    auto
    Scheduler::construct_schedule(Solution &completeSolution) -> void {
        // computes solution, value of solution, checks if solution is feasible and improving
        // breaks early if it is not.
        _initializeScheduler(completeSolution.get_start_times());
        _initializeCompleteSolution(completeSolution);
        while (!priorityQueueDepartures.empty()) {
            _getNextDeparture(completeSolution);
            if (departure.position < instance.trip_routes[departure.trip_id].size()) {
                const auto vehiclesOnArc = computeVehiclesOnArc(arrivalsOnArcs[departure.arc],
                                                                departure.time);
                const auto delay = computeDelayOnArc(vehiclesOnArc, instance, departure.arc);
                completeSolution.set_delay_on_arc(delay, departure.trip_id, departure.position);
                completeSolution.increase_total_delay(delay);
                _setNextDepartureOfVehicleAndPushToQueue(delay);
                bool scheduleIsFeasibleAndImproving = checkIfSolutionIsAdmissible(completeSolution.get_total_delay());
                if (!scheduleIsFeasibleAndImproving) {
                    completeSolution.set_feasible_and_improving_flag(false);
                }
            }
        }
    }


}