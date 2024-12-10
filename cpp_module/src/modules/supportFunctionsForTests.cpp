#include <numeric>
#include <iostream>
#include "scheduler.h"
#include <queue>
#include "pybind11/pybind11.h"
#include <fstream>
#include <filesystem>
#include <sstream>


namespace cpp_module {


    auto readVectorOfDoubles(const std::filesystem::path &Path) {
        std::ifstream inputHandler;
        inputHandler.open(Path.string());
        if (!inputHandler.is_open()) {
            throw std::invalid_argument("Input file is not open \n");
        }
        double entryOfFile;
        std::vector<double> collectionOfEntries;
        while (inputHandler >> entryOfFile) {
            collectionOfEntries.push_back(entryOfFile);
        }
        inputHandler.close();
        return collectionOfEntries;
    }

    auto readVectorOfLongs(const std::filesystem::path &Path) {
        std::ifstream inputHandler;
        inputHandler.open(Path.string());
        if (!inputHandler.is_open()) {
            throw std::invalid_argument("Input file is not open \n");
        }
        long entryOfFile;
        std::vector<long> collectionOfEntries;
        while (inputHandler >> entryOfFile) {
            collectionOfEntries.push_back(entryOfFile);
        }
        inputHandler.close();
        return collectionOfEntries;
    }

    std::vector<std::string> readCSVline(std::istringstream &iss) {
        std::string field;
        std::vector<std::string> fields;
        while (std::getline(iss, field, ',')) {
            fields.push_back(field);
        }
        return fields;
    }

    template<typename T>
    std::vector<std::vector<T>> readCSV(const std::filesystem::path &Path, int nrows = -1, int ncols = -1) {
        std::fstream ifs(Path.string());
        assert(ifs.good());
        std::vector<std::vector<T>> data;
        std::string line;
        while (getline(ifs, line)) {
            std::istringstream iss(line);
            std::vector<std::string> fields = readCSVline(iss);
            if (ncols > 0)
                assert(fields.size() == ncols);
            std::vector<T> dataVec(fields.size(), 0);
            for (int i = 0; i < fields.size(); ++i)
                dataVec[i] = stof(fields[i]);
            data.push_back(std::move(dataVec));
        }
        if (nrows > 0)
            assert(data.size() == nrows);
        return data;
    }

    struct stat info;

    auto _fixEmptyConflictingSets(
            std::vector<std::vector<long>> &importedConflictingSets) -> PotentiallyConflictingVehiclesSets {
        PotentiallyConflictingVehiclesSets conflictingSet(importedConflictingSets.size());
        for (auto i = 0; i < importedConflictingSets.size(); i++) {
            if (importedConflictingSets[i] == std::vector<long>(1, -1)) {
                continue;
            }
            for (auto vehicle: importedConflictingSets[i]) {
                conflictingSet[i].push_back(vehicle);
            }
        }
        return conflictingSet;
    }


    auto importInstanceForLocalSearch() -> ImportedInstanceForTest {
        ImportedInstanceForTest importedInstance{};
        std::filesystem::path pathToInstance =
                std::filesystem::current_path() / "../../catch2_tests/instancesForTest/instanceForLocalSearch";
        std::cout << "Searching instance in path: " << pathToInstance << "\n";
        std::filesystem::path shortestPathsFile = pathToInstance / "arcBasedShortestPaths.txt";
        std::filesystem::path earliestDeparturesFile = pathToInstance / "earliestDepartureTimes.txt";
        std::filesystem::path latestDeparturesFile = pathToInstance / "latestDepartureTimes.txt";
        std::filesystem::path releaseTimesFile = pathToInstance / "releaseTimes.txt";
        std::filesystem::path deadlinesFile = pathToInstance / "deadlines.txt";
        std::filesystem::path dueDatesFile = pathToInstance / "dueDates.txt";
        std::filesystem::path remainingSlackFile = pathToInstance / "remainingSlack.txt";
        std::filesystem::path nominalCapacitiesFile = pathToInstance / "nominalCapacitiesArcsUtilized.txt";
        std::filesystem::path nominalTravelTimesFile = pathToInstance / "travelTimesArcsUtilized.txt";
        std::filesystem::path conflictingSetsFile = pathToInstance / "conflictingSets.txt";
        std::filesystem::path parametersFile = pathToInstance / "parameters.txt";
        importedInstance.nominalCapacities = readVectorOfLongs(nominalCapacitiesFile);
        importedInstance.releaseTimes = readVectorOfDoubles(releaseTimesFile);
        importedInstance.nominalTravelTimes = readVectorOfDoubles(nominalTravelTimesFile);
        importedInstance.deadlines = readVectorOfDoubles(deadlinesFile);
        importedInstance.dueDates = readVectorOfDoubles(dueDatesFile);
        importedInstance.remainingSlack = readVectorOfDoubles(remainingSlackFile);
        importedInstance.arcBasedShortestPaths = readCSV<long>(shortestPathsFile);
        importedInstance.earliestDepartureTimes = readCSV<double>(earliestDeparturesFile);
        importedInstance.latestDepartureTimes = readCSV<double>(latestDeparturesFile);
        importedInstance.staggeringApplied = std::vector<double>(importedInstance.releaseTimes.size(), 0);
        auto importedConflictingSets = readCSV<long>(conflictingSetsFile);
        importedInstance.conflictingSets = _fixEmptyConflictingSets(importedConflictingSets);
        importedInstance.parameters = readVectorOfDoubles(parametersFile);
        return importedInstance;
    }
}

