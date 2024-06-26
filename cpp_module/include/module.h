#include <utility>
#include <vector>
#include <set>
#include <tuple>
#include <queue>
#include <limits>
#include <ctime>

//#define printsEvaluationFunction
//#define printInfoNeighborhood
//#define assertionsOnEvaluationFunction
//#define assertionsOnMoveOperator
//#define printNotEnoughSlack

namespace cppModule {
    const long ITERATION_TO_PRINT = 3; //has effect only if printsEvaluationFunction is defined
    const double CONSTR_TOLERANCE = 1 * 1e-3;
    const double TOLERANCE = 1e-6;
    const double MIN_SET_CAPACITY = 1.01;


    struct Departure {
        double time;
        long arc;
        long vehicle;
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
                if (e1.arc > e2.arc) {
                    return e1.arc > e2.arc;
                } else if (e1.arc == e2.arc) {
                    return e1.vehicle > e2.vehicle;
                } else {
                    return false;
                }
            }
            return false;

        }
    };

    using VehicleSchedule = std::vector<std::vector<double>>;
    using PotentiallyConflictingVehiclesSets = std::vector<std::vector<long>>;
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

    auto cppComputeCongestedSchedule(const std::vector<std::vector<long>> &arcBasedShortestPaths,
                                     const std::vector<double> &argReleaseTimes,
                                     const std::vector<double> &nominalTravelTimesArcs,
                                     const std::vector<long> &nominalCapacitiesArcsUtilized,
                                     const std::vector<double> &arg_list_of_slopes,
                                     const std::vector<double> &arg_list_of_thresholds,
                                     const std::vector<double> &parameters
    ) -> VehicleSchedule;

    auto cppSchedulingLocalSearch(const std::vector<double> &argReleaseTimes,
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
                                  const std::vector<double> &argParameters) -> VehicleSchedule;

    auto _sortConflicts(std::vector<Conflict> &conflictsInSchedule) -> void;

    class Instance {
    public:
        const std::vector<std::vector<long>> &arcBasedShortestPaths;
        const std::vector<double> &nominalTravelTimesArcs;
        const std::vector<long> &nominalCapacitiesArcs;
        std::vector<double> deadlines;
        std::vector<double> dueDates;
        std::vector<double> statusQuoReleaseTimes;
        PotentiallyConflictingVehiclesSets conflictingSet;
        std::vector<std::vector<double>> earliestDepartureTimes;
        std::vector<std::vector<double>> latestDepartureTimes;
        std::vector<double> freeFlowTravelTimesVehicles;
        long numberOfVehicles;
        long numberOfArcs;
        std::vector<double> list_of_slopes;
        std::vector<double> list_of_thresholds;

        double maxTimeOptimization;


        Instance(const std::vector<std::vector<long>> &argArcBasedShortestPaths,
                 const std::vector<double> &argNominalTravelTimesArcs,
                 const std::vector<long> &argNominalCapacitiesArcs,
                 const std::vector<double> &arg_list_of_slopes,
                 const std::vector<double> &arg_list_of_thresholds,
                 const std::vector<double> &argParameters
        ) :
                deadlines(argArcBasedShortestPaths.size()),
                dueDates(argArcBasedShortestPaths.size()),
                freeFlowTravelTimesVehicles(argArcBasedShortestPaths.size(), 0),
                statusQuoReleaseTimes(argArcBasedShortestPaths.size()),
                arcBasedShortestPaths(argArcBasedShortestPaths),
                nominalTravelTimesArcs(argNominalTravelTimesArcs),
                nominalCapacitiesArcs(argNominalCapacitiesArcs),
                conflictingSet(argNominalCapacitiesArcs.size()) {
            numberOfVehicles = (long) argArcBasedShortestPaths.size();
            numberOfArcs = (long) argNominalTravelTimesArcs.size();
            maxTimeOptimization = argParameters[0];
            list_of_slopes = arg_list_of_slopes;
            list_of_thresholds = arg_list_of_thresholds;

            for (auto i = 0; i < numberOfVehicles; i++) {
                deadlines[i] = std::numeric_limits<double>::max();
                dueDates[i] = std::numeric_limits<double>::max();
            }
        }
    };

    class CompleteSolution {
    public:
        VehicleSchedule congestedSchedule;
        std::vector<std::vector<bool>> tableWithCapReached;
        std::vector<double> releaseTimes;
        std::vector<double> remainingTimeSlack;
        std::vector<double> staggeringApplied;
        double totalDelay;
        double totalTardiness;
        double solutionValue;
        bool scheduleIsFeasibleAndImproving;
        bool solutionHasTies;
        bool capReached;
        long timesCapIsReached{};

        explicit CompleteSolution(const std::vector<double> &argReleaseTimes, const Instance &instance)
                : congestedSchedule(
                argReleaseTimes.size()), staggeringApplied(argReleaseTimes.size()),
                  remainingTimeSlack(
                          argReleaseTimes.size()),
                  tableWithCapReached(
                          argReleaseTimes.size()) {
            releaseTimes = argReleaseTimes;
            totalDelay = 0;
            totalTardiness = 0;
            solutionValue = 0;
            scheduleIsFeasibleAndImproving = true;
            solutionHasTies = false;
            capReached = false;
            for (auto vehicle = 0; vehicle < size(argReleaseTimes); vehicle++) {
                congestedSchedule[vehicle].resize(instance.arcBasedShortestPaths[vehicle].size());
                staggeringApplied[vehicle] = 0.0;
                remainingTimeSlack[vehicle] = std::numeric_limits<double>::max();
                tableWithCapReached[vehicle].resize(instance.arcBasedShortestPaths[vehicle].size());
            }
        };

    };


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
        const Instance &instance;
        double bestSolutionValue;
        long maxTimesCapReached;
        VehicleSchedule originalSchedule;
        VehicleSchedule scheduleToRestore;
        MinQueueDepartures priorityQueueToRestore;
//        std::vector<double> greatestTimeAnalyzedOnArcs;
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


        explicit Scheduler(const Instance &argInstance) :
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
        constructCongestedSchedule(CompleteSolution &completeSolution) -> void;

        auto
        updateExistingCongestedSchedule(CompleteSolution &completeSolution,
                                        const Conflict &conflict) -> void;

        auto _initializeScheduler(const std::vector<double> &releaseTimes) -> void;

        auto _setNextDepartureOfVehicleAndPushToQueue(double delay) -> void;

        auto _updateTotalValueSolution(CompleteSolution &completeSolution) -> void;

        void _initializeSchedulerForUpdatingCongestedSchedule(const VehicleSchedule &congestedSchedule);

        void _initializePriorityQueue(const Conflict &conflict, CompleteSolution &completeSolution);

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

        void _getNextDeparture(CompleteSolution &completeSolution);

        void _addDepartureToPriorityQueue(double releaseTimeVehicle, long vehicle);

        void _updateVehiclesOnArcOfConflictingSet(VehicleSchedule &congestedSchedule, double &vehiclesOnArc);

        void
        _decideOnVehiclesMaybeToMark(const VehicleSchedule &congestedSchedule, double currentNewArrival);

        void
        _assertNoVehiclesDepartingBeforeAreMarked(long otherVehicle, const VehicleSchedule &congestedSchedule);

        void _initializeStatusVehicles();

        void _processConflictingSet(CompleteSolution &completeSolution,
                                    double &delay,
                                    double &currentVehicleNewArrival,
                                    double &vehiclesOnArc);

        void _processVehicle(CompleteSolution &completeSolution);


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

        void _assertNoVehiclesAreLate(CompleteSolution &completeSolution);

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

        void _computeSolutionTardiness(CompleteSolution &completeSolution);

        InstructionConflictingSet
        _checkIfTripsWithinSameConflictingSetCanHaveAConflict(long otherVehicle, long otherPosition);

        void printDelayComputed(double delay) const;
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
    _applyStaggeringToSolveConflict(Scheduler &scheduler, CompleteSolution &completeSolution,
                                    Conflict &conflict) -> void;


    static auto _resetNewSolution(const CompleteSolution &currentSolution, CompleteSolution &newSolution,
                                  Conflict &conflict) -> void;

    static auto
    _updateCurrentSolution(CompleteSolution &currentSolution,
                           const CompleteSolution &newSolution,
                           Conflict &conflict) -> void;


    auto _initializeCompleteSolution(CompleteSolution &completeSolution) -> void;


    auto getIndex(const std::vector<long> &v, long K) -> long;

    auto importInstanceForLocalSearch() -> ImportedInstanceForTest;

    auto staggerVehicle(CompleteSolution &completeSolution, long vehicle, double staggering) -> void;

    auto solveSolutionTies(const Instance &instance, CompleteSolution &completeSolution, Scheduler &scheduler) -> void;

    auto checkIfSolutionHasTies(const Instance &instance, CompleteSolution &completeSolution) -> void;

    auto computeDelayOnArc(const double &vehiclesOnArc, const Instance &instance, long arc) -> double;

    auto _assertSolutionIsCorrect(CompleteSolution &newSolution, Scheduler &scheduler) -> void;

    auto
    improveTowardsSolutionQuality(const Instance &instance, CompleteSolution &currentSolution,
                                  Scheduler &scheduler) -> void;

    auto computeVehiclesOnArc(MinQueueDepartures &arrivalsOnArc, const double &departureTime) -> double;

    auto checkIfVehiclesHaveTie(const VehicleSchedule &congestedSchedule, const Tie &tie) -> bool;

    auto initializeConflictingSetsForConstructSchedule(Instance &instance) -> void;
}
