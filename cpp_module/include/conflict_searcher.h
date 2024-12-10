#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <stdexcept> // For std::out_of_range


namespace cpp_module {

    class ConflictSearcherNew {
    public:
        struct vehicleInfo {
            long trip_id;
            double departureTime;
            double arrivalTime;
            double earliestDepartureTime;
            double earliestArrivalTime;
            double latestDepartureTime;
            double latestArrivalTime;
        };

        struct ConflictingArrival {
            long vehicle;
            double arrival;
        };

        enum InstructionsConflict {
            CONTINUE, ADD_CONFLICT, BREAK
        };

        const Instance &instance;
        vehicleInfo currentVehicleInfo{};
        vehicleInfo other_info{};
        ConflictingArrival conflictingArrival{};
        std::vector<ConflictingArrival> conflictingArrivals;

        explicit ConflictSearcherNew(const Instance &argInstance) :
                instance(argInstance) {}


        std::vector<Conflict> getConflictsListNew(const VehicleSchedule &congestedSchedule);

        bool _checkIfVehicleHasDelay(const VehicleSchedule &congestedSchedule, long currentVehicle);

        void updateCurrentVehicleInfo(long currentVehicle, const VehicleSchedule &congestedSchedule, long position);

        InstructionsConflict getInstructionsConflict(const VehicleSchedule &congestedSchedule, long other_position);

        Conflict _createConflictNew(long arc, double delay, ConflictingArrival &sortedArrival) const;

        void addConflictsToConflictsList(std::vector<Conflict> &conflictsList, long arc);

        static bool compareConflictingArrivals(const ConflictingArrival &a, const ConflictingArrival &b) {
            return a.arrival < b.arrival;
        }
    };
}