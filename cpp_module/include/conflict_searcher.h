#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <stdexcept> // For std::out_of_range

namespace cpp_module {

    class ConflictSearcherNew {
    public:
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

        explicit ConflictSearcherNew(const Instance &arg_instance) :
                instance(arg_instance) {}

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

    };
}
