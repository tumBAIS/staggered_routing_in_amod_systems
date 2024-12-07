#!/bin/bash

# General Job-related configuration
source my_cluster_configuration.sh
export JOB_NAME=$MY_JOB_NAME
export MEMORY_PER_CPU=$MY_MEMORY_PER_CPU
export MINUTES_PER_RUN=$MY_MINUTES_PER_RUN
export EMAIL="antonio.coppola@tum.de"
# Command to execute. Will be run with arguments from the
# run list file.
export EXECUTABLE="./executable"
# Resources
# How many CPUs each run requires
export CPUS_PER_RUN=$MY_CPU_PER_RUN
# Specify the memory required *per cpu*. The memory requested
# per run is MEMORY_PER_CPU*CPUS_PER_RUN. Suffixes can be [K|M|G|T]
#export MEMORY_PER_CPU=$MY_MEMORY_PER_CPU
# Maximum time limit is 5h
#export MINUTES_PER_RUN=$MY_MINUTES_PER_RUN
# Can be 1 or 0
export GPUS_PER_RUN=0
# Possible choices: urgent > normal
export QOS=$MY_PRIORITY
# On which nodes to run, possible values: CPU_ONLY, GPU_ONLY, ANY
export NODE_TYPE=$MY_NODE_TYPE

# Set up your environment here, e.g., load modules, activate virtual environments
module unload python
module unload gurobi
module load cmake/
module load gurobi/10.0.0
module load python/3.11.9
module load gcc/11.1.0
module load gdal/3.4.2
source venv/bin/activate
dos2unix run_list.csv
rm joblog.csv

# build cpp_module library
echo "Did you remember to build the cpp libraries? If no, run ./build_cpp_module.sh"
#rm -r cpp_module/cmake-build-release
#cmake -S cpp_module/ -B cpp_module/cmake-build-release -DCMAKE_BUILD_TYPE=Release
#cmake --build cpp_module/cmake-build-release --target cpp_module


#Print out some info
echo "JOB_NAME: ${MY_JOB_NAME}"

# Defaults for other run-related variables.
# These can be ignored in most cases: they are utilized by dispatch_instance.sh
export BASE_DIR=$(pwd)
RUN_LIST="run_list.csv"
export RESULTS_DIRECTORY="results"
export LOGS_DIRECTORY="logs"
export ERROR_LOGS_DIRECTORY="error-logs"
export SCRIPTS_DIRECTORY="scripts"
export CONSOLE_LOG_NAME="console.log"
export ERROR_CONSOLE_LOG_NAME="console-error.log"
