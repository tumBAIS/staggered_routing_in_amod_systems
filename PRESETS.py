PRESETS = {
    "var_pwl_paper": {
        "network_name": "manhattan_100",
        "number_of_trips": 5000,
        "day_list": list(range(1, 32)),  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5], [0.5, 0.7], [0.5, 0.7, 0.9]],
        "list_of_thresholds_list": [[1], [1, 1.5], [1, 1.5, 2]],
        "staggering_cap_list": [25],
        "deadline_factor": 100,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True],
        "simplify": True,
        "verbose_model": True,
        "local_search_callback": True  # end solver params
    },
    "no_ls_comparison_mini": {
        "network_name": "manhattan_10",
        "number_of_trips": 500,
        "day_list": list(range(1, 11)),  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[.5]],
        "list_of_thresholds_list": [[1]],
        "staggering_cap_list": [10],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True, False],
        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True  # end solver params
    },
    "no_ls_comparison_paper": {
        "network_name": "manhattan_100",
        "number_of_trips": 5000,
        "day_list": list(range(1, 32)),  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5, 0.9, 1.1]],
        "list_of_thresholds_list": [[1, 1.8, 2]],
        "staggering_cap_list": [10],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True, False],
        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True  # end solver params
    },
    "algo_performance_mini": {
        "network_name": "manhattan_10",
        "number_of_trips": 500,
        "day_list": list(range(1, 12)),  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[.5]],
        "list_of_thresholds_list": [[1]],
        "staggering_cap_list": [10],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE", "ONLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True],

        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True  # end solver params
    },
    "algo_performance_paper": {
        "network_name": "manhattan_100",
        "number_of_trips": 5000,
        "day_list": list(range(1, 32)),  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5, 0.9, 1.1]],
        "list_of_thresholds_list": [[1, 1.8, 2]],
        "staggering_cap_list": [10],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE", "ONLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True],
        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True  # end solver params
    },
    "check_instances": {
        "network_name": "manhattan_100",
        "max_length_shortcut": 1500,
        "number_of_trips": 5000,
        "day_list": list(range(1, 32)),  # start instance params
        "max_flow_allowed_list": [10, 15, 20, 25, 30, 35],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5, 0.9, 1.1]],
        "list_of_thresholds_list": [[1, 1.8, 2]],
        "staggering_cap_list": [10, 20],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": False,
        "warm_start": False,
        "improve_warm_start_list": [False],
        "simplify": False,
        "verbose_model": False,
        "local_search_callback": False,  # end solver params
        "job_priority": "URGENT",
        "cpu_per_run": 1,
        "node_type": "CPU_ONLY",
        "minutes_per_run": 10,
        "memory_per_cpu": "2000MB",
    },
    "algo_performance_future_paper": {
        "network_name": "manhattan_100",
        "max_length_shortcut": 1500,
        "number_of_trips": 5000,
        "day_list": list(range(16, 32)),  # start instance params
        "max_flow_allowed_list": [35, 30, 25, 20],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5, 0.9, 1.1]],
        "list_of_thresholds_list": [[1, 1.8, 2]],
        "staggering_cap_list": [20, 10],
        "deadline_factor": 25,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True],
        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True,  # end solver params
        "job_priority": "NORMAL",
        "cpu_per_run": 1,
        "node_type": "CPU_ONLY",
        "minutes_per_run": 60 * 2,
        "memory_per_cpu": "16000MB",
    },

    "staggering_analysis_paper": {
        "network_name": "manhattan_100",
        "number_of_trips": 5000,
        "day_list": [3],  # start instance params
        "max_flow_allowed_list": [20, 40],
        "seed_list": [0],
        "list_of_slopes_list": [[0.5, 0.9, 1.1]],
        "list_of_thresholds_list": [[1, 1.8, 2]],
        "staggering_cap_list": [x * 2.5 for x in range(11)],  # Generates [0.0, 2.5, 5.0, ..., 25.0]
        "deadline_factor": 100,  # end instance params
        "algo_mode_list": ["OFFLINE"],
        "optimize": True,
        "warm_start": True,
        "improve_warm_start_list": [True],
        "simplify": True,
        "verbose_model": False,
        "local_search_callback": True  # end solver params
    },
}
