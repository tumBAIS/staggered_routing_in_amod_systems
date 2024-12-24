#ifndef CATCH_CONFIG_MAIN
#define CATCH_CONFIG_MAIN  // This tells Catch to provide a main() - only do this in one cpp file
#endif

#include "../lib/json.hpp"
#include "catch.hpp"
#include "local_search.h"

using json = nlohmann::json;
using namespace cpp_module;

auto load_json(const std::string &file_path) -> json {
    // Open the JSON file
    std::ifstream file(file_path);
    if (!file.is_open()) {
        throw std::runtime_error("Unable to open file for reading: " + file_path);
    }

    // Parse the JSON object
    nlohmann::json json_obj;
    file >> json_obj;  // Load JSON data from file
    file.close();
    std::cout << "JSON file successfully loaded from " << file_path << std::endl;  // Print success message

    return json_obj;
}


TEST_CASE("Local search validation") {
    std::cout << "Current working directory: "
              << std::filesystem::current_path() << std::endl;
    std::string file_path = "../../catch2_tests/files_for_testing/test_ls.json";
    auto json_obj = load_json(file_path);
    Instance instance = Instance::from_json(json_obj);
    LocalSearch local_search(instance);
    auto solution = local_search.run(const_cast<std::vector<Time> &>(instance.get_release_times()));
}

TEST_CASE("Offline solution validation") {
    std::cout << "Current working directory: "
              << std::filesystem::current_path() << std::endl;
    std::string file_path = "../../catch2_tests/files_for_testing/test_offline_solution.json";
    auto json_obj = load_json(file_path);
    Instance instance = Instance::from_json(json_obj);
    Scheduler scheduler(instance);
    auto solution = scheduler.construct_solution(instance.get_release_times());
}
