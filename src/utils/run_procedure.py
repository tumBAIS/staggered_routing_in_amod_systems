from instanceModule.instance import save_instance_for_testing_cpp_code
from solutions.reconstructSolution import reconstruct_solution
from inputData import get_input_data
from utils.imports import get_not_simplified_instance
from instanceModule.epochInstance import get_epoch_instances
from solutions.statusQuo import get_current_epoch_status_quo
from solutions.core import get_offline_solution, get_epoch_solution
from instanceModule.updateEpochInstance import update_next_epoch_instance
from processing.simplify import simplify_system
from utils.prints import print_insights_algorithm
from utils.save import save_experiment


def run_procedure(source: str) -> None:
    input_data = get_input_data(source)
    global_instance = get_not_simplified_instance(input_data)
    epoch_instances = get_epoch_instances(global_instance)
    epoch_solutions = []
    for epoch_id, epoch_instance in enumerate(epoch_instances):
        epoch_instance = epoch_instances[epoch_id]
        epoch_status_quo = get_current_epoch_status_quo(epoch_instance)
        simplified_instance, simplified_status_quo = simplify_system(epoch_instance, epoch_status_quo)
        epoch_solution = get_epoch_solution(simplified_instance, simplified_status_quo, epoch_instance,
                                            epoch_status_quo)
        epoch_solutions.append(epoch_solution)
        if epoch_id < len(epoch_instances) - 1:
            next_epoch_instance = epoch_instances[epoch_id + 1]
            update_next_epoch_instance(epoch_instance, epoch_solution, next_epoch_instance, global_instance)

    # reconstruct the status quo from the available information
    complete_status_quo = get_offline_solution(global_instance, global_instance.releaseTimesDataset)
    reconstructed_solution = reconstruct_solution(epoch_instances, epoch_solutions, global_instance)
    print_insights_algorithm(complete_status_quo, reconstructed_solution, epoch_instances)
    save_experiment(source, global_instance, complete_status_quo, reconstructed_solution)
    save_instance_for_testing_cpp_code(global_instance, complete_status_quo)
