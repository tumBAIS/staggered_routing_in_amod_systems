# Staggered Routing for Autonomous Mobility-on-Demand Systems

Welcome to the repository for "Staggered Routing in Autonomous Mobility-on-Demand Systems". This research, conducted by
Antonio Coppola, Gerhard Hiermann, Dario Paccagnan, and Maximilian Schiffer, introduces a novel approach for optimizing
departure times in a fleet of autonomous taxis. Our goal is to minimize congestion within urban street networks,
enhancing efficiency and reducing travel times.

For a deeper dive into our methodologies and findings, please refer to our paper: [https://arxiv.org/abs/2405.01410]

## Getting Started

### Prerequisites

Before running the code, ensure you have the following installed:

- Python >= 3.11
- An appropriate C++ compiler for pybind11 integration

### Installation

1. **Clone the Repository**
   To get started with the project, clone this repository to your local machine:
   ```bash
   git clone <repository-url>
   ```

2. **Environment Setup**

- Mark the `src` folder as a source directory in your IDE to help it recognize project files.
- Install the required Python packages:
  ```bash
  pip install -r requirements.txt
  ```
  Note: For issues with Fiona or GDAL installations, consider using wheel files available
  at [Gohlke's Pythonlibs](https://www.lfd.uci.edu/~gohlke/pythonlibs/).

3. **C++ Module Integration**

- Navigate to `cpp_module/lib` and follow the instructions in `readme.md` to install pybind11. Note that the following
  instructions were tested on WindowsOS .
- To ensure compatibility and ease of setup, `pybind11` version 2.13.6 is included directly via git. To install this
  specific version, from the `cpp_module` directory run the following command:
  ```bash
  Invoke-WebRequest -Uri "https://github.com/pybind/pybind11/archive/refs/tags/v2.13.6.zip" -OutFile "pybind11-v2.13.6.zip"
  Expand-Archive -Path "pybind11-v2.13.6.zip" -DestinationPath "lib"
  Remove-Item -Path "pybind11-v2.13.6.zip"
  ```
- Rename the extracted directory to `pybind11`:
  ```bash
  Rename-Item -Path "lib\pybind11-2.13.6" -NewName "pybind11"
  ```

- Navigate to the C++ Module Directory: Locate the directory containing the C++ module, typically found under
  `cpp_module/`.

- Compile the Code: Use your preferred C++ compiler or build system to compile the code. If you're using CMake, a
  typical command sequence might be:
  ```bash
  mkdir build
  cd build
  cmake .. -DCMAKE_BUILD_TYPE=Release
  make
  ```

- After building the C++ module, inform the Python code about the build type you chose:
    - **Open `src/input_data.py`**: Locate and open the `src/input_data.py` file in your project's source directory.
    - **Set the `C_MAKE_CONFIGURATION` Variable**: Find the `C_MAKE_CONFIGURATION` variable and set it to the build type
      you used. For example, if you compiled the C++ code with a release configuration, change the line to:
      ```python
      C_MAKE_CONFIGURATION = "release"
      ```

### Data Download Instructions

This project utilizes NYC datasets hosted on Zenodo. Download the zip file and place it into the `data` directory of
this project.

```bash
Invoke-WebRequest -Uri "https://zenodo.org/records/10844603/files/YellowTripData2015-01.zip?download=1" -OutFile "data.zip"
Expand-Archive -Path "data.zip" -DestinationPath "data"
Remove-Item -Path "data.zip"
```

### Run a Simulation

To run the simulation, execute `main.py`. Both the instance and the solver parameters can be specified in
`src/input_data.py` in the function `generate_input_data_from_script`. If the instance file does not exist, the code
will automatically create it before running the actual simulation.

#### Input Parameters

The `input_parameters` comprise:

- `day`: NYC Taxi Data day.
- `number_of_trips`: Number of trips to sample from the taxi trips occurring between 4 PM and 5 PM.
- `seed`: Affects the sample.
- `network_name`: Must be `manhattan_X`, with `X` being the percentage of nodes to retain (e.g., `manhattan_100`).
- `max_flow_allowed`: in seconds/vehicle, defines capacities on arcs.
- `add_shortcuts`: if `True`, adds contraction hierarchies shortcuts to the network.
- `list_of_slopes`: Defines the slopes of the travel time function (e.g., `[0.15, 0.2]`). Values must be increasing to
  ensure convexity. The number of entries defines the number of pieces of the function.
- `list_of_thresholds`: Defines the breakpoints of the travel time function (e.g., `[1, 2]`). Needs to be the same
  length as `list_of_slopes`.
- `deadline_factor`: Computes the deadline as `travel time + deadline_factor * travel_time`.
- `staggering_cap`: Assigns maximum staggering time as `staggering_cap * travel_time`.

The `solver_parameters` are:

- `epoch_size`: In minutes. If 60, solves the offline version of the problem; if less (e.g., 6), solves the online
  version.
- `epoch_time_limit`: Max time (in seconds) for the algorithm to find a solution for the epoch.
- `optimize`: If `True`, solves the MILP model.
- `warm_start`: If `True`, gives an initial solution to the MILP model.
- `improve_warm_start`: If `True`, feeds the status quo (uncontrolled solution) to local search before feeding it into
  the MILP.
- `local_search_callback`: If `True`, improves new incumbents with local search.
- `simplify`: If `True`, switches to multigraph representation, which reduces arc variables.
- `set_of_experiments`: If not `None`, specifies the name of the subfolder of `sets_of_experiments` where to save
  results.
- `verbose_model`: If `True`, prints additional info on the solving process.

### Results

The results are stored in the subdirectory of `data` associated with the parameterization of the experiment. If
`set_of_experiments` is passed, then results are also stored in `sets_of_experiments/set_of_experiments` subfolder.

Solutions and figures utilized in the paper are hosted on
Zenodo: [download link](https://zenodo.org/records/14650799/files/sets_of_experiments.zip?download=1&preview=1). Each
analysis has its own folder in

`sets_of_experiments`:

- `ALGO_PERF`: Contains experiments, figures, and tables regarding instance descriptions, delay reductions achieved,
  optimality gaps, arc delay distributions, and congestion heatmaps.
- `VAR_PWL`: Contains analysis of delay reductions achieved for various parameterizations of the piecewise linear travel
  time functions.
- `NO_LS_COMPARISON`: Contains a comparison of the performance of the algorithm against the simple MILP.
- `STAGGERING_ANALYSIS`: Contains sensitivity analysis of delay reductions achieved for various `staggering_cap` values.

### Gurobi Optimizer

This project utilizes the Gurobi Optimizer for advanced optimizations, which requires a valid license for full
functionality.

#### Obtaining a Gurobi License

- **Academic License**: Eligible academic institution affiliates can obtain a free license through the Gurobi website.
- **Commercial License**: For commercial purposes, review licensing options and pricing on the Gurobi website.

For detailed information on licensing and installation, please consult
the [Gurobi documentation](https://www.gurobi.com/documentation/).

Ensure Gurobi is correctly installed and licensed on your system prior to running this project.

## Support

For any queries or technical issues, please open an issue on this repository or contact the contributors directly via
email.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
