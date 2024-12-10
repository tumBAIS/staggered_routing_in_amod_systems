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
            double departure_time;
            double arrival_time;
            double earliest_departure_time;
            double latest_departure_time;
            double latest_arrival_time;
        };

        struct ConflictingArrival {
            long vehicle;
            double arrival;
        };

        enum InstructionsConflict {
            CONTINUE, ADD_CONFLICT, BREAK
        };

        const Instance &instance;
        vehicleInfo current_vehicle_info{};
        vehicleInfo other_info{};
        std::vector<ConflictingArrival> conflicting_arrivals;

        explicit ConflictSearcherNew(const Instance &argInstance) :
                instance(argInstance) {}


        static bool compare_conflicting_arrivals(const ConflictingArrival &a, const ConflictingArrival &b) {
            return a.arrival < b.arrival;
        }


        std::vector<Conflict> get_conflicts_list(const VehicleSchedule &congested_schedule);

        bool check_vehicle_delay(const VehicleSchedule &congested_schedule, long current_vehicle);

        void
        update_current_vehicle_info(long current_vehicle, const VehicleSchedule &congested_schedule, long position);

        void add_conflicts_to_list(std::vector<Conflict> &conflicts_list, long arc);

        InstructionsConflict get_conflict_instructions(const VehicleSchedule &congested_schedule, long other_position);


        [[nodiscard]] Conflict create_conflict(long arc, double delay, const ConflictingArrival &sorted_arrival) const;
    };
}