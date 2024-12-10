#include "stdexcept"
#include <utility>
#include <algorithm>
#include <iostream>
#include <queue>
#include "scheduler.h"


namespace cpp_module {


    struct Entry {
        long vehicle;
        long position;
        long arc;
        double time;
    };

    bool CompareEntries(const Entry &e1, const Entry &e2) {
        if (e1.time < e2.time) {
            return e1.time < e2.time;
        } else if (e1.time == e2.time) {
            if (e1.arc < e2.arc) {
                return e1.arc < e2.arc;
            } else if (e1.arc == e2.arc) {
                return e1.vehicle < e2.vehicle;
            } else {
                return false;
            }
        }
        return false;
    }


    auto _assertSolutionIsCorrect(Solution &newSolution, Scheduler &scheduler) -> void {
#ifdef assertionsOnMoveOperator
        // check with old function if outputs coincide
        cppModule::CompleteSolution testSolution(newSolution);
        scheduler.constructCongestedSchedule(testSolution);

        if (abs(testSolution.totalDelay - newSolution.totalDelay) > cppModule::TOLERANCE) {
            std::cout << "Total delay new function : " << newSolution.totalDelay;
            std::cout << " \n Total delay old function : " << testSolution.totalDelay << "\n";
            std::cout << "Total delay is wrong! \n";
            std::cout << "Iteration of scheduler: " << scheduler.iteration << "\n";
        }

        checkIfSolutionHasTies(scheduler.instance, testSolution);
        checkIfSolutionHasTies(scheduler.instance, newSolution);
        if (testSolution.solutionHasTies || newSolution.solutionHasTies) {
            std::cout << "Solution have ties \n";
        }

        if (testSolution.timesCapIsReached != newSolution.timesCapIsReached) {
            std::cout << "Times cap is reached new function " << newSolution.timesCapIsReached;
            std::cout << " \n Times cap is reached new function : " << testSolution.timesCapIsReached;
        }
        for (auto vehicle = 0; vehicle < scheduler.instance.numberOfVehicles; vehicle++) {

            // check if deadline is met
            if (newSolution.congestedSchedule[vehicle].back() > scheduler.instance.deadlines[vehicle] + TOLERANCE) {
                std::cout << " Vehicle " << vehicle << " arrives late: deadline: "
                          << scheduler.instance.deadlines[vehicle] << " arrival: "
                          << newSolution.congestedSchedule[vehicle].back();
            }

            if (abs(newSolution.congestedSchedule[vehicle][0] - newSolution.releaseTimes[vehicle]) >
                cppModule::TOLERANCE) {
                std::cout << " Start time in congested schedule of vehicle " << vehicle << " : "
                          << newSolution.congestedSchedule[vehicle][0];
                std::cout << " Release time of vehicle " << vehicle << " : " << newSolution.releaseTimes[vehicle]
                          << "\n";
            }
        }


        Entry entryOld{};
        Entry entryNew{};
        std::vector<Entry> allTheEventsNewSolutionSorted;
        std::vector<Entry> allTheEventsTestSolutionSorted;
        for (long vehicle = 0; vehicle < scheduler.instance.numberOfVehicles; vehicle++) {
            for (long arcIndex = 0;
                 arcIndex < scheduler.instance.arcBasedShortestPaths[vehicle].size(); arcIndex++) {

                entryOld.time = testSolution.congestedSchedule[vehicle][arcIndex];
                entryOld.vehicle = vehicle;
                entryOld.arc = scheduler.instance.arcBasedShortestPaths[vehicle][arcIndex];
                entryOld.position = arcIndex;

                entryNew.time = newSolution.congestedSchedule[vehicle][arcIndex];
                entryNew.vehicle = vehicle;
                entryNew.arc = scheduler.instance.arcBasedShortestPaths[vehicle][arcIndex];
                entryNew.position = arcIndex;


                allTheEventsNewSolutionSorted.push_back(entryNew);
                allTheEventsTestSolutionSorted.push_back(entryOld);
            }
        }


        std::sort(allTheEventsNewSolutionSorted.begin(), allTheEventsNewSolutionSorted.end(), CompareEntries);
        std::sort(allTheEventsTestSolutionSorted.begin(), allTheEventsTestSolutionSorted.end(), CompareEntries);
        bool startPrint = false;
        int numEntriesToPrint = 0;
        for (auto entryId = 0; entryId < allTheEventsNewSolutionSorted.size(); entryId++) {
            bool entriesDiffer =
                    abs(allTheEventsNewSolutionSorted[entryId].time -
                        allTheEventsTestSolutionSorted[entryId].time) >
                    cppModule::TOLERANCE;
            if (entriesDiffer) {
                startPrint = true;
            }
            if (startPrint && numEntriesToPrint < 1000) {
                numEntriesToPrint++;
                std::cout << "Entry id: " << entryId << " - New Time: "
                          << allTheEventsNewSolutionSorted[entryId].time
                          << " New Vehicle: " << allTheEventsNewSolutionSorted[entryId].vehicle
                          << " New Arc: " << allTheEventsNewSolutionSorted[entryId].arc
                          << " New Position: " << allTheEventsNewSolutionSorted[entryId].position
                          << " -- Old Time: " << allTheEventsTestSolutionSorted[entryId].time
                          << " Old Vehicle: " << allTheEventsTestSolutionSorted[entryId].vehicle
                          << " Old Arc: " << allTheEventsTestSolutionSorted[entryId].arc
                          << " Old Position: " << allTheEventsTestSolutionSorted[entryId].position;
                if (entriesDiffer) {
                    std::cout << " - entries differ ++++++\n";
                } else {
                    std::cout << "\n";
                }
            }
        }
        if (startPrint) {
            throw std::invalid_argument("Solution provided by new evaluation function is incorrect");
        }
#endif
    }


}