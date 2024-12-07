file(GLOB_RECURSE CATCH_SOURCES "${PROJECT_SOURCE_DIR}/catch2_tests/*.cpp")
add_executable(catch2_tests ${CATCH_SOURCES})

target_include_directories(catch2_tests PRIVATE ${PROJECT_SOURCE_DIR}/include)
target_include_directories(catch2_tests PRIVATE ${PROJECT_SOURCE_DIR}/lib/catch2/include)

target_link_libraries(catch2_tests PRIVATE cpp_module_catch2)
target_link_libraries(catch2_tests PRIVATE project_options)
