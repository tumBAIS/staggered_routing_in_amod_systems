# Import necessary modules and functions
from input_data import get_input_data
from solutions.status_quo import get_epoch_status_quo, get_cpp_instance
from solutions.core import get_offline_solution, get_epoch_solution
from simplify.simplify import simplify_system
from utils.prints import print_insights_algorithm
from utils.save import save_experiment
from problem.epoch_instance import get_epoch_instance


def run_procedure(source: str) -> None:
    """
    Main procedure to run the entire simulation.
    """
    from problem.instance import get_instance

    # Load initial data and setup instances
    instance_params, solver_params = get_input_data(source)
    instance = get_instance(instance_params)
    cpp_instance = get_cpp_instance(instance, solver_params.epoch_time_limit)
    complete_status_quo = get_offline_solution(instance, cpp_instance)
    if not solver_params.optimize:
        return save_experiment(instance, complete_status_quo, solver_params)

    # Initialize a list to store solutions for each epoch
    epoch_solutions = []
    epoch_instances = []
    optimization_measures_list = []
    # Process each epoch instance
    number_of_epochs = 60 // solver_params.epoch_size
    map_previous_epoch_trips_to_start_time = None
    for epoch_id in range(number_of_epochs):
        # Start processing instance
        epoch_instance = get_epoch_instance(instance, epoch_id, solver_params, map_previous_epoch_trips_to_start_time)

        epoch_instance.print_start(solver_params.epoch_size)

        # Get the status quo for the current epoch
        epoch_status_quo, cpp_epoch_instance = get_epoch_status_quo(epoch_instance, solver_params)

        # Simplify the system for the current epoch
        simplified_instance, simplified_status_quo = simplify_system(epoch_instance, epoch_status_quo, solver_params)

        # Solve for the current epoch
        epoch_solution, optimization_measures = get_epoch_solution(simplified_instance, simplified_status_quo,
                                                                   epoch_instance, epoch_status_quo, solver_params,
                                                                   cpp_epoch_instance)

        map_previous_epoch_trips_to_start_time = epoch_solution.get_map_previous_epoch_trips_to_start_time(
            epoch_instance,
            solver_params,
            epoch_id)

        # Store epoch info
        epoch_solutions.append(epoch_solution)
        epoch_instances.append(epoch_instance)
        optimization_measures_list.append(optimization_measures)

    # Reconstruct the complete solution from all epochs
    from solutions.reconstruct_solution import reconstruct_solution

    reconstructed_solution = reconstruct_solution(epoch_instances, epoch_solutions, cpp_instance)

    # Print insights and save the results
    print_insights_algorithm(complete_status_quo, reconstructed_solution, epoch_instances)
    instance.remove_arc_copies()
    save_experiment(instance, complete_status_quo, solver_params,
                    optimization_measures_list, reconstructed_solution)
