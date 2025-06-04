#!/bin/bash
# Handles job directory setup before execution.
# Configures SLURM job submission settings, including CPUs, GPUs, and memory.
# Determines the type of compute node (CPU, GPU).
# Submits the job using srun and logs output.
# Implements error handling, calling on_error.sh if the job fails.

# ----------------------------------------
# Set up directories for this run
# ----------------------------------------

export TARGET_DIR_NAME=$1  # Will utilize the job name given by the user

# Ensure the main job directory exists before proceeding
if [ ! -d "${BASE_DIR}/${SETS_OF_EXPERIMENTS_DIRECTORY}/${JOB_NAME}" ]; then
    mkdir -p "${BASE_DIR}/${SETS_OF_EXPERIMENTS_DIRECTORY}/${JOB_NAME}/errors"
    mkdir -p "${BASE_DIR}/${SETS_OF_EXPERIMENTS_DIRECTORY}/${JOB_NAME}/logs"
fi

# Define paths for logs and errors
export TARGET_LOG_DIRECTORY="${BASE_DIR}/${SETS_OF_EXPERIMENTS_DIRECTORY}/${JOB_NAME}/logs/${TARGET_DIR_NAME}"
export TARGET_ERROR_LOG_DIRECTORY="${BASE_DIR}/${SETS_OF_EXPERIMENTS_DIRECTORY}/${JOB_NAME}/errors/${TARGET_DIR_NAME}"

# Create required log directory if it doesn't exist
if [ ! -e "${TARGET_LOG_DIRECTORY}" ]; then
    mkdir -p "${TARGET_LOG_DIRECTORY}"
fi

# Define log file paths
export TARGET_STDOUT_LOG="${TARGET_LOG_DIRECTORY}/${CONSOLE_LOG_NAME}"
export TARGET_STDERR_LOG="${TARGET_LOG_DIRECTORY}/${ERROR_CONSOLE_LOG_NAME}"

# Debugging: Print directory paths
echo "Log Directory: ${TARGET_LOG_DIRECTORY}"
echo "Error Log Directory: ${TARGET_ERROR_LOG_DIRECTORY}"

# ----------------------------------------
# Set SLURM Node Type Constraints
# ----------------------------------------

case ${NODE_TYPE} in
    "GPU_ONLY")
        _NODES="--exclude=osm-cpu-[1-6]"
        ;;
    "CPU_ONLY")
        _NODES="--exclude=osm-gpu-[1-5]"
        ;;
    "GPU_2_ONLY")
        _NODES="--nodelist=osm-gpu-[2]"
        ;;
    "ANY")
        _NODES=""
        ;;
    *)
        echo "Error: Unknown node type: ${NODE_TYPE}"
        exit 1
        ;;
esac

# ----------------------------------------
# Submit Job to SLURM
# ----------------------------------------

srun -n 1 \
    --job-name="${TARGET_DIR_NAME}" \
    --cpus-per-task=${CPUS_PER_RUN} \
    --gpus-per-task=${GPUS_PER_RUN} \
    --mem-per-cpu=${MEMORY_PER_CPU} \
    --time=${MINUTES_PER_RUN} \
    --qos="${QOS}" \
    ${_NODES} \
    --export=ALL \
    --output="${TARGET_STDOUT_LOG}" \
    --error="${TARGET_STDERR_LOG}" \
    "${BASE_DIR}/${SCRIPTS_DIRECTORY}/dispatch_instance.sh" "$@"

slurm_status_code=$?

# ----------------------------------------
# Handle Errors if Job Fails
# ----------------------------------------

if [ $slurm_status_code -ne 0 ]; then
    echo "Job failed with exit code ${slurm_status_code}. Saving logs to error directory."

    # Copy logs to error directory
    cp -a "${TARGET_LOG_DIRECTORY}/." "${TARGET_ERROR_LOG_DIRECTORY}/"

    # Run error handling script
    "${BASE_DIR}/${SCRIPTS_DIRECTORY}/on_error.sh" ${slurm_status_code} "${TARGET_DIR_NAME}" "$@"
fi

# Exit with SLURM job's exit code
exit ${slurm_status_code}
