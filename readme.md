# Staggered Routing for Autonomous Mobility-on-Demand Systems

Welcome to the repository for "Staggered Routing in Autonomous Mobility-on-Demand Systems". This research, 
conducted by Antonio Coppola, Gerhard Hiermann, Dario Paccagnan, and Maximilian Schiffer, 
introduce a novel approach for optimizing departure times in a fleet of autonomous taxis. 
Our goal is to minimize congestion within urban street networks, enhancing efficiency  and reducing travel times.

For a deeper dive into our methodologies and findings, please refer to our paper: [Link to the paper]

## Getting Started

### Prerequisites

Before running the code, ensure you have the following installed:
- Python >= 3.9 
- An appropriate C++ compiler for pybind11 integration

### Installation

1. **Clone the Repository**
   To get started with the project, clone this repository to your local machine: `git clone <repository-url>`

2. **Environment Setup**
- Mark the 'src' folder as a source directory in your IDE to help it recognize project files.
- Install the required Python packages: `pip install -r requirements.txt`
  Note: For issues with Fiona or GDAL installations, consider using wheel files available at [Gohlke's Pythonlibs](https://www.lfd.uci.edu/~gohlke/pythonlibs/).

3. **C++ Module Integration**
- Navigate to `cpp_module/lib` and follow the instructions in `readme.md` to install pybind11.
- Navigate to the C++ Module Directory: Locate the directory containing the C++ module, typically found under `cpp_module/`.
 -Compile the Code: Use your preferred C++ compiler or build system to compile the code. If you're using CMake, a typical command sequence might be:

   ```bash
   mkdir build
   cd build
   cmake .. -DCMAKE_BUILD_TYPE=Release
   make
  
- After building the C++ module, you must inform the Python code about the build type you chose. 
  -**Open `inputData.py`**: Locate and open the `inputData.py` file in your project's source directory.
  -**Set the `C_MAKE_CONFIGURATION` Variable**: Find the `C_MAKE_CONFIGURATION` variable and set it to the build type you used. For example, if you compiled the C++ code with a release configuration, change the line to:
   ```python
   C_MAKE_CONFIGURATION = "release"

### Generating the Instances

#### Data Download Instructions

This project utilizes datasets hosted on Zenodo. Follow the instructions below to download and set up the data in the `data` directory of this project.

```bash
 Invoke-WebRequest -Uri "https://zenodo.org/records/10844603/files/YellowTripData2015-01.zip?download=1" -OutFile "data.zip"
 Expand-Archive -Path "data.zip" -DestinationPath "data"
 Remove-Item -Path "data.zip"
```



To run the simulation, you must first generate the instances by creating the necessary data files. This process is facilitated by the script `create_instance.py`, which populates the `data` folder with `network.json` and `instance.json` files. These files contain essential information about the simulation instance:

- `network.json`: This file is a serialized representation of a networkx graph, detailing the network structure.
- `instance.json`: Contains the x and y coordinates for the origin and destination of each trip, along with their respective release times. Additional parameters, such as the maximum staggering time and deadlines, are set during runtime.

#### Configuration Options

When running `create_instance.py`, you can specify various settings to tailor the instance generation to your needs. The available options include:

- `type_of_instance`: Defines the source of the ride data.
  - `synthetic`: Generates synthetic ride requests.
  - `all_true_data`: Uses all real ride requests originating and terminating within the specified district and time window.
  - `sampled_true_rides`: Samples `n` real ride requests based on the specified criteria.
- `t_min`: The length of the time window in minutes, starting from 4 PM on the selected day. Applies to real ride data.
- `seed`: Sets the random seed for generating synthetic data and sampling from real data, ensuring reproducibility.
- `day`: Selects the day for which real ride data is used, applicable only for real data from January 1 to January 31, 2015.
- `number_of_rides`: Determines the number of trips to generate or sample. Relevant for `synthetic` and `sampled_true_rides` options.
- `place`: Specifies the district in Manhattan for which the network is generated.

### Running the Code
After setting up your environment and compiling the C++ module, you can start the application by running:
`python online.py`
The parameterization of the runs can be done in the file `src.inputData.py`

### Results
The results are stored in the subdirectory of `data` associated to the parameterization of the experiment.


## External Dependencies and Licensing

### Gurobi Optimizer
This project utilizes the Gurobi Optimizer for advanced optimizations, which requires a valid license for full functionality. 

#### Obtaining a Gurobi License
- **Academic License**: Eligible academic institution affiliates can obtain a free license through the Gurobi website.
- **Commercial License**: For commercial purposes, review licensing options and pricing on the Gurobi website.

For detailed information on licensing and installation, please consult the [Gurobi documentation](https://www.gurobi.com/documentation/).

Ensure Gurobi is correctly installed and licensed on your system prior to running this project.

## Support

For any queries or technical issues, please open an issue on this repository or contact the contributors directly via email.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
