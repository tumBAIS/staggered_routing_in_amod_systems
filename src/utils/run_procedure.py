# Import necessary modules and functions
from solutions.reconstruct_solution import reconstruct_solution
from input_data import get_input_data
from utils.imports import get_not_simplified_instance
from instance_module.epoch_instance import get_epoch_instances
from solutions.status_quo import get_current_epoch_status_quo
from solutions.core import get_offline_solution, get_epoch_solution
from instance_module.update_epoch_instance import update_next_epoch_instance
from processing.simplify import simplify_system
from utils.prints import print_insights_algorithm
from utils.save import save_experiment


def run_procedure(source: str) -> None:
    """
    Main procedure to run the entire simulation.
    """
    # Load initial data and setup instances
    instance_params, solver_params = get_input_data(source)
    global_instance = get_not_simplified_instance(instance_params)
    epoch_instances = get_epoch_instances(global_instance, solver_params)

    # Initialize a list to store solutions for each epoch
    epoch_solutions = []
    optimization_measures_list = []
    # Process each epoch instance
    for epoch_id, epoch_instance in enumerate(epoch_instances):
        # Get the status quo for the current epoch
        epoch_status_quo = get_current_epoch_status_quo(epoch_instance, solver_params)

        # Simplify the system for the current epoch
        simplified_instance, simplified_status_quo = simplify_system(epoch_instance, epoch_status_quo)

        # Solve for the current epoch
        epoch_solution, optimization_measures = get_epoch_solution(simplified_instance, simplified_status_quo,
                                                                   epoch_instance,
                                                                   epoch_status_quo, solver_params)
        epoch_solutions.append(epoch_solution)
        optimization_measures_list.append(optimization_measures)
        # Update the instance for the next epoch if not the last one
        if epoch_id < len(epoch_instances) - 1:
            next_epoch_instance = epoch_instances[epoch_id + 1]
            update_next_epoch_instance(epoch_instance, epoch_solution, next_epoch_instance, global_instance,
                                       solver_params)

    # Reconstruct the complete solution from all epochs
    complete_status_quo = get_offline_solution(global_instance, global_instance.release_times_dataset, solver_params)
    reconstructed_solution = reconstruct_solution(epoch_instances, epoch_solutions, global_instance)

    # Print insights and save the results
    print_insights_algorithm(complete_status_quo, reconstructed_solution, epoch_instances)
    save_experiment(global_instance, complete_status_quo, reconstructed_solution, solver_params,
                    optimization_measures_list)
