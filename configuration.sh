#!/bin/bash

# ----------------------------------------
# Load General Job Configuration
# ----------------------------------------

source my_cluster_configuration.sh

# Set job-related environment variables
export JOB_NAME=$MY_JOB_NAME
export MEMORY_PER_CPU=$MY_MEMORY_PER_CPU
export MINUTES_PER_RUN=$MY_MINUTES_PER_RUN
export EMAIL="antonio.coppola@tum.de"

# Command to execute; will run with arguments from the run list file
export EXECUTABLE="./executable"

# ----------------------------------------
# Resource Allocation
# ----------------------------------------

# Number of CPUs required per run
export CPUS_PER_RUN=$MY_CPU_PER_RUN

# Specify memory required per CPU (total: MEMORY_PER_CPU * CPUS_PER_RUN)
export MEMORY_PER_CPU=$MY_MEMORY_PER_CPU  # This was duplicated in the original script

# Maximum time limit per run
export MINUTES_PER_RUN=$MY_MINUTES_PER_RUN

# Number of GPUs required per run (0 = no GPUs)
export GPUS_PER_RUN=0

# Job Priority (QoS) - Possible choices: urgent > normal
export QOS=$MY_PRIORITY

# Node type: CPU_ONLY, GPU_ONLY, ANY
export NODE_TYPE=$MY_NODE_TYPE

# ----------------------------------------
# Load Required Modules & Set Up Environment
# ----------------------------------------

module unload python
module unload gurobi
module load cmake/
module load gurobi/10.0.0
module load python/3.11.9
module load gcc/11.1.0
module load gdal/3.4.2
source venv/bin/activate
dos2unix run_list.csv

# build cpp_module library
echo "Did you remember to build the cpp libraries? If no, run ./build_cpp_module.sh"
 

# ----------------------------------------
# Print Job Info
# ----------------------------------------

echo "JOB_NAME: ${MY_JOB_NAME}"

# ----------------------------------------
# Set Up Directory Paths
# ----------------------------------------

export BASE_DIR=$(pwd)
export RUN_LIST="run_list.csv"
export RESULTS_DIRECTORY="results"
export LOGS_DIRECTORY="logs"
export ERROR_LOGS_DIRECTORY="error-logs"
export SETS_OF_EXPERIMENTS_DIRECTORY="sets_of_experiments"
export SCRIPTS_DIRECTORY="scripts"
export CONSOLE_LOG_NAME="console.log"
export ERROR_CONSOLE_LOG_NAME="console-error.log"