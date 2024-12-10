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
    const double CONSTR_TOLERANCE = 1 * 1e-3;
    const double TOLERANCE = 1e-6;


    struct Departure {
        double time;
        long arc;
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
                return e1.arc > e2.arc;
            }
            return false;

        }
    };

    using MinQueueDepartures = std::priority_queue<Departure, std::vector<Departure>, CompareDepartures>;

    struct Conflict {
        long arc;
        long currentVehicle;
        long otherVehicle;
        double delayConflict;
        double distanceToCover;
        double staggeringCurrentVehicle;
        double destaggeringOtherVehicle;
    };

    struct ImportedInstanceForTest {
        std::vector<double> releaseTimes;
        std::vector<double> deadlines;
        std::vector<double> dueDates;
        std::vector<double> staggeringApplied;
        std::vector<double> remainingSlack;
        std::vector<double> nominalTravelTimes;
        std::vector<long> nominalCapacities;
        std::vector<std::vector<long>> arcBasedShortestPaths;
        std::vector<std::vector<double>> earliestDepartureTimes;
        std::vector<std::vector<double>> latestDepartureTimes;
        PotentiallyConflictingVehiclesSets conflictingSets;
        std::vector<double> parameters;


    };

    auto cppSchedulingLocalSearch(const std::vector<double> &arg_release_times,
                                  const std::vector<double> &argRemainingTimeSlack,
                                  const std::vector<double> &argStaggeringApplied,
                                  const PotentiallyConflictingVehiclesSets &argConflictingSets,
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
        std::vector<long> lastProcessedPosition;
        std::vector<long> numberOfReInsertions;
        std::vector<long> vehiclesToMaybeMark;
        Departure departure{};
        Departure otherVehicleDeparture{};
        Instance &instance;
        double bestSolutionValue;
        long maxTimesCapReached;
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
        std::vector<vehicleStatusType> vehicleStatus;
        long iteration;
        long lateSolutions = 0;
        long worseSolutions = 0;
        long slackNotEnough = 0;
        long solutionWithTies = 0;
        long exploredSolutions = 0;
        long noStaggeringAppliedSolutions = 0;
        bool slackIsEnough = true;


        explicit Scheduler(Instance &argInstance) :
                instance(argInstance) {
            startSearchClock = clock() / (double) CLOCKS_PER_SEC;
            bestSolutionValue = std::numeric_limits<double>::max();
            maxTimesCapReached = std::numeric_limits<long>::max();
            vehicleStatus = std::vector<vehicleStatusType>(instance.numberOfVehicles, vehicleStatusType::INACTIVE);
            iteration = 0;
        };

        auto
        checkIfSolutionIsAdmissible(double totalDelay, double timesCapIsReached) -> bool;

        auto
        construct_schedule(Solution &completeSolution) -> void;

        auto
        updateExistingCongestedSchedule(Solution &completeSolution,
                                        const Conflict &conflict) -> void;

        auto _initializeScheduler(const std::vector<double> &releaseTimes) -> void;

        auto _setNextDepartureOfVehicleAndPushToQueue(double delay) -> void;

        auto _updateTotalValueSolution(Solution &completeSolution) -> void;

        void _initializeSchedulerForUpdatingCongestedSchedule(const VehicleSchedule &congestedSchedule);

        void _initializePriorityQueue(const Conflict &conflict, Solution &completeSolution);

        auto _checkIfOtherShouldBeMarked(long otherVehicle, long otherPosition,
                                         bool currentConflictsWithOther) -> vehicleShouldBeMarked;

        [[nodiscard]] bool
        _checkConflictWithOtherVehicle(long otherVehicle, double otherDeparture, double otherArrival) const;

        bool _checkIfShouldMarkGivenCurrentArrivalTime(long otherVehicle, double currentVehicleNewArrival);

        void _markVehicle(long otherVehicle, double otherDeparture, long otherPosition);

        void
        moveVehicleForwardInTheQueue(double currentVehicleNewArrival);

        bool _checkIfOtherStartsBeforeCurrent(long otherVehicle, const VehicleSchedule &congestedSchedule);

        bool _checkIfDepartureShouldBeSkipped();

        auto _checkIfActivationDepartureShouldBeSkipped() -> bool;

        auto _checkIfTravelDepartureShouldBeSkipped() -> bool;

        void _updateVehicleSchedule(VehicleSchedule &congestedSchedule,
                                    double currentNewArrival) const;

        void _activateStagingVehicle();

        void _reinsertOtherInQueue(VehicleSchedule &congestedSchedule,
                                   long otherVehicle,
                                   long otherPosition,
                                   double otherDeparture,
                                   long arc);

        void _assertEventPushedToQueueIsCorrect();

        void _getNextDeparture(Solution &completeSolution);

        void _addDepartureToPriorityQueue(double releaseTimeVehicle, long vehicle);

        void _updateVehiclesOnArcOfConflictingSet(VehicleSchedule &congestedSchedule, double &vehiclesOnArc);

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

        void _assertDepartureIsFeasible(VehicleSchedule &congestedSchedule);

        void _assertLazyUpdateIsNecessary(double otherDeparture) const;

        void _assertNoVehiclesAreLate(Solution &completeSolution);

        void _assertVehiclesOnArcIsCorrect(double vehiclesOnArc, VehicleSchedule &congestedSchedule);

        void _resetOtherScheduleToReinsertionTime(VehicleSchedule &congestedSchedule, long otherVehicle,
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

        bool _checkIfVehicleIsLate(double currentVehicleNewArrival);

        static void assertTotalTardinessIsNotNegative(double totalTardiness);

        void _computeSolutionTardiness(Solution &completeSolution);

        InstructionConflictingSet
        _checkIfTripsWithinSameConflictingSetCanHaveAConflict(long otherVehicle, long otherPosition);

        void printDelayComputed(double delay) const;


        Solution construct_solution(const std::vector<double> &start_times);
    };

    class ConflictSearcherNew {
    public:
        struct vehicleInfo {
            long vehicle;
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
        vehicleInfo otherVehicleInfo{};
        ConflictingArrival conflictingArrival{};
        std::vector<ConflictingArrival> conflictingArrivals;

        explicit ConflictSearcherNew(const Instance &argInstance) :
                instance(argInstance) {}


        std::vector<Conflict> getConflictsListNew(const VehicleSchedule &congestedSchedule);

        bool _checkIfVehicleHasDelay(const VehicleSchedule &congestedSchedule, long currentVehicle);

        void updateCurrentVehicleInfo(long currentVehicle, const VehicleSchedule &congestedSchedule, long position);

        InstructionsConflict getInstructionsConflict(const VehicleSchedule &congestedSchedule, long otherPosition);

        Conflict _createConflictNew(long arc, double delay, ConflictingArrival &sortedArrival) const;

        void addConflictsToConflictsList(std::vector<Conflict> &conflictsList, long arc);

        static bool compareConflictingArrivals(const ConflictingArrival &a, const ConflictingArrival &b) {
            return a.arrival < b.arrival;
        }
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

    auto importInstanceForLocalSearch() -> ImportedInstanceForTest;

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
