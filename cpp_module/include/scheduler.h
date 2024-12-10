#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>
#include <stdexcept>  // Include for std::out_of_range
#include "solution.h"

//#define printsEvaluationFunction
//#define printInfoNeighborhood
//#define assertionsOnEvaluationFunction
//#define assertionsOnMoveOperator
//#define printNotEnoughSlack

namespace cpp_module {
    const long ITERATION_TO_PRINT = 3; //has effect only if printsEvaluationFunction is defined


    struct Departure {
        double time;
        long arc_id;
        long trip_id;
        long position;
        enum {
            TRAVEL, ACTIVATION
        } eventType;
        long reinsertionNumber;
    };


    struct Tie {
        long vehicleOne;
        long vehicleTwo;
        long positionOne;
        long positionTwo;
        long arc;
    };


    struct CompareDepartures {
        bool operator()(Departure const &e1, Departure const &e2) {
            if (e1.time > e2.time) {
                return e1.time > e2.time;
            } else if (e1.time == e2.time) {
                return e1.arc_id > e2.arc_id;
            }
            return false;

        }
    };

    using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;


    auto cppSchedulingLocalSearch(const std::vector<double> &arg_release_times,
                                  const std::vector<double> &argRemainingTimeSlack,
                                  const std::vector<double> &argStaggeringApplied,
                                  const ConflictingSetsList &argConflictingSets,
                                  const std::vector<std::vector<double>> &earliestDepartureTimes,
                                  const std::vector<std::vector<double>> &latestDepartureTimes,
                                  const std::vector<double> &argNominalTravelTimesArcs,
                                  const std::vector<long> &argNominalCapacitiesArcsUtilized,
                                  const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                  const std::vector<double> &argDeadlines,
                                  const std::vector<double> &argDueDates,
                                  const std::vector<double> &arg_list_of_slopes,
                                  const std::vector<double> &arg_list_of_thresholds,
                                  const std::vector<double> &argParameters,
                                  const double &lb_travel_time) -> VehicleSchedule;

    auto _sortConflicts(std::vector<Conflict> &conflictsInSchedule) -> void;


    class Scheduler {
        using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;
    public:
        MinQueueDepartures priorityQueueDepartures;
        std::vector<MinQueueDepartures> arrivalsOnArcs;
        std::vector<long> last_processed_position;
        std::vector<long> number_of_reinsertions;
        std::vector<long> vehiclesToMaybeMark;
        Departure departure{};
        Departure otherVehicleDeparture{};
        Instance &instance;
        double best_total_delay;
        VehicleSchedule originalSchedule;
        VehicleSchedule scheduleToRestore;
        MinQueueDepartures priorityQueueToRestore;
        bool lazyUpdatePriorityQueue{};
        bool tieFound{};
        bool vehicleIsLate{};
        enum vehicleStatusType {
            INACTIVE, STAGING, ACTIVE
        };
        enum vehicleShouldBeMarked {
            YES, NO, MAYBE
        };

        enum InstructionConflictingSet {
            CONTINUE, EVALUATE, BREAK
        };
        double startSearchClock;
        std::vector<vehicleStatusType> trip_status_list;
        long iteration;
        long worseSolutions = 0;
        long slackNotEnough = 0;
        long solutionWithTies = 0;
        long exploredSolutions = 0;
        bool slackIsEnough = true;


        explicit Scheduler(Instance &argInstance) :
                instance(argInstance) {
            startSearchClock = clock() / (double) CLOCKS_PER_SEC;
            best_total_delay = std::numeric_limits<double>::max();
            trip_status_list = std::vector<vehicleStatusType>(instance.get_number_of_trips(),
                                                              vehicleStatusType::INACTIVE);
            iteration = 0;
        };

        [[nodiscard]] auto
        checkIfSolutionIsAdmissible(double totalDelay) const -> bool;

        auto
        construct_schedule(Solution &completeSolution) -> void;

        auto
        updateExistingCongestedSchedule(Solution &completeSolution,
                                        const Conflict &conflict) -> void;

        auto _initializeScheduler(const std::vector<double> &releaseTimes) -> void;

        auto _setNextDepartureOfVehicleAndPushToQueue(double delay) -> void;

        auto _updateTotalValueSolution(Solution &completeSolution) -> void;

        void _initializeSchedulerForUpdatingCongestedSchedule(const VehicleSchedule &congestedSchedule);

        void _initializePriorityQueue(const Conflict &conflict, Solution &solution);

        auto _checkIfOtherShouldBeMarked(long otherVehicle, long otherPosition,
                                         bool currentConflictsWithOther) -> vehicleShouldBeMarked;

        [[nodiscard]] bool
        _checkConflictWithOtherVehicle(long otherVehicle, double otherDeparture, double otherArrival) const;

        bool _checkIfShouldMarkGivenCurrentArrivalTime(long other_trip_id, double currentVehicleNewArrival);

        void _markVehicle(long otherVehicle, double otherDeparture, long otherPosition);

        void
        moveVehicleForwardInTheQueue(double currentVehicleNewArrival);

        [[nodiscard]] bool
        _checkIfOtherStartsBeforeCurrent(long other_trip_id, const VehicleSchedule &congestedSchedule) const;

        bool _checkIfDepartureShouldBeSkipped();

        auto _checkIfActivationDepartureShouldBeSkipped() -> bool;

        auto _checkIfTravelDepartureShouldBeSkipped() -> bool;

        void _updateVehicleSchedule(Solution &solution, double currentNewArrival) const;

        void _activateStagingVehicle();

        void _reinsertOtherInQueue(Solution &congestedSchedule,
                                   long otherVehicle,
                                   long otherPosition,
                                   double otherDeparture,
                                   long arc);

        void _assertEventPushedToQueueIsCorrect();

        void _getNextDeparture(Solution &completeSolution);

        void _addDepartureToPriorityQueue(double releaseTimeVehicle, long vehicle);

        void _updateVehiclesOnArcOfConflictingSet(Solution &solution, double &vehiclesOnArc);

        void
        _decideOnVehiclesMaybeToMark(const VehicleSchedule &congestedSchedule, double currentNewArrival);

        void
        _assertNoVehiclesDepartingBeforeAreMarked(long otherVehicle, const VehicleSchedule &congestedSchedule);

        void _initializeStatusVehicles();

        void _processConflictingSet(Solution &completeSolution,
                                    double &delay,
                                    double &currentVehicleNewArrival,
                                    double &vehiclesOnArc);

        void _processVehicle(Solution &completeSolution);


        void _assertOtherIsNotActive(long otherVehicle);

        [[nodiscard]] bool
        _checkIfOtherIsFirstInOriginalSchedule(long otherVehicle, double otherOriginalDeparture,
                                               double currentOriginalDeparture) const;

        [[nodiscard]] bool
        _checkIfOtherIsFirstInCurrentSchedule(long otherVehicle, double otherOriginalDeparture) const;

        [[nodiscard]] bool _checkIfCurrentOverlappedWithOther(long otherVehicle,
                                                              double otherOriginalDeparture,
                                                              double currentOriginalDeparture,
                                                              double otherOriginalArrival) const;

        [[nodiscard]] bool _checkIfOtherOverlappedWithCurrent(long otherVehicle, double otherOriginalDeparture,
                                                              double currentOriginalDeparture,
                                                              double currentOriginalArrival) const;

        [[nodiscard]] bool _checkIfOtherOverlapsNowWithCurrent(long otherVehicle, double otherOriginalDeparture,
                                                               double currentVehicleNewArrival) const;

        static bool _checkConditionsToMark(bool switchCurrentWithOtherOrder, bool vehiclesNeverOverlapped,
                                           bool currentAlwaysFirst, bool otherAlwaysOverlaps);

        void _printUpdateGreatestTimeAnalyzed() const;

        void _printDeparturePushedToQueue() const;


        bool _checkIfTieInSet(const VehicleSchedule &congestedSchedule);

        void _assertDepartureIsFeasible(const VehicleSchedule &congestedSchedule);

        void _assertLazyUpdateIsNecessary(double otherDeparture) const;

        void _assertNoVehiclesAreLate(Solution &completeSolution);

        void _assertVehiclesOnArcIsCorrect(double vehiclesOnArc, const VehicleSchedule &congestedSchedule);

        void _resetOtherScheduleToReinsertionTime(Solution &solution, long otherVehicle,
                                                  long otherPosition);

        void _assertAnalyzingSmallestDeparture(VehicleSchedule &congestedSchedule);

        void _assertOtherStartsAfterIfHasToBeProcessedOnThisArcNext(long otherVehicle, long otherPosition,
                                                                    double otherDeparture);

        void _assertCombinationStatusAndDepartureTypeIsPossible();

        void _printReinsertionVehicle(const long &arc, const long &vehicle, const double &departureTime) const;

        void _printDeparture() const;

        void printLazyUpdatePriorityQueue() const;

        void printIterationNumber() const;

        void printTravelDepartureToSkip();

        [[nodiscard]] bool _checkIfVehicleIsLate(double currentVehicleNewArrival) const;


        [[nodiscard]] InstructionConflictingSet
        _check_if_trips_within_conflicting_set_can_conflict(long other_trip_id, long other_position) const;

        void printDelayComputed(double delay) const;


        Solution construct_solution(const std::vector<double> &start_times);
    };


    auto
    _applyStaggeringToSolveConflict(Scheduler &scheduler, Solution &completeSolution,
                                    Conflict &conflict) -> void;


    static auto _resetNewSolution(const Solution &currentSolution, Solution &newSolution,
                                  Conflict &conflict) -> void;

    static auto
    _updateCurrentSolution(Solution &currentSolution,
                           const Solution &newSolution,
                           Conflict &conflict) -> void;


    auto _initializeCompleteSolution(Solution &completeSolution) -> void;


    auto getIndex(const std::vector<long> &v, long K) -> long;


    auto staggerVehicle(Solution &completeSolution, long vehicle, double staggering) -> void;

    auto solveSolutionTies(const Instance &instance, Solution &completeSolution, Scheduler &scheduler) -> void;

    auto checkIfSolutionHasTies(const Instance &instance, Solution &completeSolution) -> void;

    auto computeDelayOnArc(const double &vehiclesOnArc, const Instance &instance, long arc) -> double;

    auto _assertSolutionIsCorrect(Solution &newSolution, Scheduler &scheduler) -> void;

    auto
    improveTowardsSolutionQuality(const Instance &instance, Solution &currentSolution,
                                  Scheduler &scheduler) -> void;

    auto computeVehiclesOnArc(MinQueueDepartures &arrivalsOnArc, const double &departureTime) -> double;

    auto checkIfVehiclesHaveTie(const VehicleSchedule &congestedSchedule, const Tie &tie) -> bool;

    auto initializeConflictingSetsForConstructSchedule(Instance &instance) -> void;
}