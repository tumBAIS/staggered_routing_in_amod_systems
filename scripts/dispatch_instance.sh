#!/bin/bash
# Automates running HPC jobs.
# Manages temporary directories for execution and cleanup.
# Handles logging by saving SLURM job details.
# Executes a pre-run setup (prepare.sh) and a post-run cleanup (epilog.sh).
# Handles errors gracefully and logs them for debugging.
# Copies results and logs back to shared storage.

# ----------------------------------------
# Function: gather_and_setup
# Sets up required directories and symbolic links
# ----------------------------------------

function gather_and_setup() {
    for dir in $(ls "${BASE_DIR}"); do
        case "${dir}" in
            "${RESULTS_DIRECTORY}"|"${ERROR_LOGS_DIRECTORY}"|"${LOGS_DIRECTORY}") ;;
            *)
                ln -s "${BASE_DIR}/${dir}"
                ;;
        esac
    done

    # Create local directories for output files
    mkdir -p "${RESULTS_DIRECTORY}"
    mkdir -p "${ERROR_LOGS_DIRECTORY}"
    mkdir -p "${LOGS_DIRECTORY}"
}

# ----------------------------------------
# Initialize Job
# ----------------------------------------

RUN_NAME=$1
shift
exit_code=0

# Create a unique temporary directory on the local filesystem
RUN_DIRECTORY=$(mktemp -d -p /var/scratch "job-template-XXXXXXXXX")

if [ $? -ne 0 ]; then
    echo "[Template]: Error, could not create temp dir with prefix (${RUN_NAME}) in /var/scratch"
    exit 1
fi

cd "${RUN_DIRECTORY}"

# ----------------------------------------
# Run Setup Function
# ----------------------------------------

gather_and_setup
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "[Template]: Error, directory setup failed: $exit_code"
    exit $exit_code
fi

# Execute pre-run setup script
"${BASE_DIR}/${SCRIPTS_DIRECTORY}/prepare.sh"
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "[Template]: Error running \"${BASE_DIR}/${SCRIPTS_DIRECTORY}/prepare.sh\": $exit_code"
    exit $exit_code
fi

# ----------------------------------------
# Execute Main Job
# ----------------------------------------

echo "--------- Start of ${EXECUTABLE} ---------"
${EXECUTABLE} "$@"
executable_exit_code=$?
echo "--------- End of ${EXECUTABLE} ---------"

# ----------------------------------------
# Execute Post-run Cleanup
# ----------------------------------------

"${BASE_DIR}/${SCRIPTS_DIRECTORY}/epilog.sh"
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "[Template]: Error running \"${BASE_DIR}/${SCRIPTS_DIRECTORY}/epilog.sh\": $exit_code"
    exit $exit_code
fi

# ----------------------------------------
# Copy Output Files to Shared Storage
# ----------------------------------------

if [ $executable_exit_code -ne 0 ]; then
    echo "[Template]: Error running \"${EXECUTABLE} $@\": $executable_exit_code. See ${TARGET_ERROR_LOG_DIRECTORY}"
fi

# Ensure logs are copied


if [ -d "logs" ] && [ -n "$(ls -A logs/ 2>/dev/null)" ]; then
    cp -a logs/* "${TARGET_LOG_DIRECTORY}/"
fi


# Ensure results are copied if they exist (Uncomment if needed)
# cp -a results/* "${TARGET_RESULTS_DIRECTORY}/"

# ----------------------------------------
# Cleanup Temporary Directory
# ----------------------------------------

cd /tmp
rm -rf "${RUN_DIRECTORY}"

# Exit with the executable's status code
exit ${executable_exit_code}
