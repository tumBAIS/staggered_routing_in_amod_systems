from pathlib import Path
from pandas import DataFrame


def get_arc_congestion_distribution_barplot(results_df: DataFrame, path_to_figures: Path) -> None:
    # TODO: in this figure we have three frequency barplots next to eachother (see reference picture).
    # The first step is to divide results_df in the offline_df (solver_parameters_epoch_size == 60) and in the
    # online_df (the others). We then can retrieve in instance_trip_routes column the routes of the trips
    # (it is a list[[list[int]] where int here is the arc identifier of the trip).
    # The identifier 0 is a dummy arc. so it can be ignored.
    # To create the first barplot

