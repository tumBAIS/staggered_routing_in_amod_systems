#include "catch.hpp"
#include "module.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include "filesystem"

namespace cpp_module {


    auto _printFirstNPaths(const ImportedInstanceForTest &importedInstance, const long n) -> void {
        std::cout << "Head of paths: \n";
        for (auto i = 0; i < n; i++) {
            std::cout << " Path " << i << ": ";
            for (long j: importedInstance.arcBasedShortestPaths[i]) {
                std::cout << j << " ";
            }
            std::cout << "\n";
        }
        std::cout << "\n";
    }

    auto _printFirstNConflictingSets(const ImportedInstanceForTest &importedInstance, const long n) -> void {
        std::cout << "Head of conflicting sets: \n";
        for (auto i = 0; i < n; i++) {
            std::cout << " Conflicting Set of arc " << i << ": ";
            for (long j: importedInstance.conflictingSets[i]) {
                std::cout << j << " ";
            }
            std::cout << "\n";
        }
        std::cout << "\n";
    }

    TEST_CASE("testCreateCongestedSchedule") {
        ImportedInstanceForTest importedInstance = importInstanceForLocalSearch();
        auto vehicleSchedule = cppComputeCongestedSchedule(importedInstance.arcBasedShortestPaths,
                                                           importedInstance.releaseTimes,
                                                           importedInstance.nominalTravelTimes,
                                                           importedInstance.nominalCapacities,
                                                           importedInstance.parameters);
    }; // end test_case 1

    TEST_CASE("testLocalSearch") {
        ImportedInstanceForTest importedInstance = importInstanceForLocalSearch();
        _printFirstNPaths(importedInstance, 5);
        _printFirstNConflictingSets(importedInstance, 5);
        auto vehicleSchedule = cppSchedulingLocalSearch(importedInstance.releaseTimes,
                                                        importedInstance.remainingSlack,
                                                        importedInstance.staggeringApplied,
                                                        importedInstance.conflictingSets,
                                                        importedInstance.earliestDepartureTimes,
                                                        importedInstance.latestDepartureTimes,
                                                        importedInstance.nominalTravelTimes,
                                                        importedInstance.nominalCapacities,
                                                        importedInstance.arcBasedShortestPaths,
                                                        importedInstance.deadlines,
                                                        importedInstance.dueDates,
                                                        importedInstance.parameters);
    }; // end test_case 2


}

