from instanceModule.instance import saveInstanceForTestingCppCode
from solutions.reconstructSolution import reconstructSolution
from inputData import getInputData
from utils.imports import getNotSimplifiedInstance
from instanceModule.epochInstance import getEpochInstances
from solutions.statusQuo import getCurrentEpochStatusQuo
from solutions.core import getOfflineSolution, getEpochSolution
from instanceModule.updateEpochInstance import updateNextEpochInstance
from processing.simplify import simplifySystem
from utils.prints import printInsightsAlgorithm
from utils.save import saveExperiment


def runProcedure(inputSource: str) -> None:
    inputData = getInputData(inputSource)
    globalInstance = getNotSimplifiedInstance(inputData)
    epochInstances = getEpochInstances(globalInstance)
    epochSolutions = []
    for epochID, epochInstance in enumerate(epochInstances):
        epochInstance = epochInstances[epochID]
        epochStatusQuo = getCurrentEpochStatusQuo(epochInstance)
        simplifiedInstance, simplifiedStatusQuo = simplifySystem(epochInstance, epochStatusQuo)
        epochSolution = getEpochSolution(simplifiedInstance, simplifiedStatusQuo, epochInstance, epochStatusQuo)
        epochSolutions.append(epochSolution)
        if epochID < len(epochInstances) - 1:
            nextEpochInstance = epochInstances[epochID + 1]
            updateNextEpochInstance(epochInstance, epochSolution, nextEpochInstance, globalInstance)

    # reconstruct the status quo from the available information
    completeStatusQuo = getOfflineSolution(globalInstance, globalInstance.releaseTimesDataset)
    reconstructedSolution = reconstructSolution(epochInstances, epochSolutions, globalInstance)
    printInsightsAlgorithm(completeStatusQuo, reconstructedSolution, epochInstances)
    saveExperiment(inputSource, globalInstance, completeStatusQuo, reconstructedSolution)
    saveInstanceForTestingCppCode(globalInstance, completeStatusQuo)
