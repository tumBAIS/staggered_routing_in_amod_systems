import os
import sys
from pathlib import Path
import matplotlib
import warnings

# ===========================
# Set Paths
# ===========================
path_to_repo = Path(__file__).parent.parent.parent
path_to_src = path_to_repo / "src"
os.chdir(path_to_repo.as_posix())

# ===========================
# C++ Build Configuration
# ===========================
build = "release"  # Options: release, debug, relwithdebinfo
path_to_build = path_to_repo / f"cpp_module/cmake-build-{build}"
sys.path.append(path_to_build.as_posix())
sys.path.append(path_to_src.as_posix())

# ===========================
# Import Custom Modules
# ===========================
from instance_generator.computer import InstanceComputer
from input_data import InstanceParameters

# ===========================
# Matplotlib Configuration
# ===========================
# Suppress specific matplotlib warning
warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive, and thus cannot be shown")
# Use Agg backend for non-GUI environments
matplotlib.use('Agg')

if __name__ == "__main__":
    # ===========================
    # Instance Parameters
    # ===========================
    instance_params = InstanceParameters(
        day=1,
        number_of_trips=100,
        seed=0,
        network_name="manhattan_10",
        max_flow_allowed=100,
        add_shortcuts=False,
        list_of_slopes=[0.05],
        list_of_thresholds=[1],
        deadline_factor=100,
        staggering_cap=10,
    )

    # ===========================
    # Run Instance Computation
    # ===========================
    InstanceComputer(instance_params).run()
