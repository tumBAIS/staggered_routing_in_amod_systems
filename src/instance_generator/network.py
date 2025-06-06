from statistics import mean, median, stdev
import geopandas as gpd
import jsonpickle
import networkx as nx
import shapely as shp
from networkx.readwrite import json_graph
from shapely import Polygon

from input_data import InstanceParameters
from instance_generator.arc import Arc
from typing import Optional


class Network:

    def __init__(self, input_data: InstanceParameters, G: Optional[nx.DiGraph] = None):
        self.instance_params = input_data
        if G is None:
            # From run_procedure
            self.G = self._deserialize(self.instance_params.path_to_G)
        else:
            # From generate instance
            self.G = G
        self._store_osm_id()
        self._relabel_nodes_to_integers()
        self.gdf_nodes = self._get_gdf_nodes()
        self.arcs = []
        self.travel_time_arcs = []
        self.nominal_capacities_arcs = []
        self.arc_map = {}
        self.map_arc_trip_path_position = []

    def __str__(self):
        return f"{self.instance_params.network_name}_{len(self.G.nodes)}_nodes_{len(self.G.edges)}_edges"

    def __repr__(self):
        return f"{self.instance_params.network_name}_{len(self.G.nodes)}_nodes_{len(self.G.edges)}_edges"

    @property
    def polygon(self) -> Polygon:
        return self.gdf_nodes.unary_union.convex_hull

    @staticmethod
    def _deserialize(file_path) -> nx.DiGraph:
        """Function to _deserialize a NetworkX MultiDiGraph from a JSON file."""
        with open(file_path, 'r+') as _file:
            call_graph = json_graph.adjacency_graph(jsonpickle.decode(_file.read()), directed=True)
        return nx.DiGraph(call_graph)

    def _relabel_nodes_to_integers(self) -> None:
        """
        Relabel the names of the nodes of a graph G to integers (0, 1, 2, ...) in-place.
        """
        # Store the osmid (e.g. 1831) as an attribute in data

        # Create the mapping of node names to integers dict[osm_id, id]
        mapping = {node: i for i, node in enumerate(self.G.nodes())}

        try:
            # Attempt to relabel nodes in-place
            nx.relabel_nodes(self.G, mapping, copy=False)
        except nx.NetworkXUnfeasible:
            print("In-place relabeling failed due to overlapping labels, performing copy relabeling instead.")
            # Perform relabeling with a copy to avoid conflicts
            self.G = nx.relabel_nodes(self.G, mapping, copy=True)
        return

    def _store_osm_id(self):
        for osm_id, data in self.G.nodes(data=True):
            self.G.nodes[osm_id]['osmid'] = osm_id

    def find_closest_node(self, point: shp.Point):
        """
        Finds the closest node in a graph to a given point. Assumes both point and graph geometries are in meters.

        Parameters:
        - graph: A networkx.Graph object where nodes have 'x' and 'y' attributes representing coordinates in meters.
        - point: A shapely.geometry.Point object representing the point of interest, in meters.

        Returns:
        The node in the graph closest to the point.
        """

        # Use the geometry directly for querying nearest
        nearest_indexes = list(self.gdf_nodes.sindex.nearest(point, return_distance=False))

        # Retrieve the closest node information from the GeoDataFrame
        nearest_index = nearest_indexes[1]
        nearest_node = self.gdf_nodes.iloc[nearest_index]

        return int(nearest_node.index[0])

    def _get_gdf_nodes(self) -> gpd.GeoDataFrame:
        """ Convert NetworkX graph nodes to a list of dictionaries for GeoDataFrame """
        nodes = [{'node': node, 'geometry': shp.Point(data['x'], data['y'])} for node, data in self.G.nodes(data=True)]
        # Set the 'node' column as the index of the DataFrame
        nodes_gdf = gpd.GeoDataFrame(nodes, geometry='geometry')
        nodes_gdf.set_index('node', inplace=True)
        nodes_gdf.sort_index(inplace=True)
        return nodes_gdf

    def add_arcs(self, trips):
        """
        Add both dummy arcs (for disjoint paths) and real arcs (from OSM data) to the internal lists.
        """
        # Get OSM arcs utilized by trips
        osm_arcs_utilized = trips.get_osm_arcs_utilized()

        # Add dummy arcs (one for each alternative path)
        dummy_arc = Arc.create_dummy_arc(id=0)
        self.arcs.append(dummy_arc)
        self.travel_time_arcs.append(dummy_arc.nominal_travel_time)  # This will always be 0 for dummy arcs
        self.nominal_capacities_arcs.append(dummy_arc.nominal_capacity)  # This will always be 0 or 1 for dummy arcs

        # Add real arcs from OSM data, starting with an ID after the dummy arcs
        for id_offset, osm_arc_id in enumerate(osm_arcs_utilized, start=1):
            osm_arc_info = self.G.edges[osm_arc_id]  # Get OSM info from the graph
            arc = Arc(id=id_offset, osm_info=osm_arc_info, max_flow_allowed=self.instance_params.max_flow_allowed)
            self.arcs.append(arc)
            self.travel_time_arcs.append(arc.nominal_travel_time)
            self.nominal_capacities_arcs.append(arc.nominal_capacity)
            self.arc_map[osm_arc_id] = id_offset  # Map OSM arc ID to internal arc ID

        # Optionally print information about the arcs
        self.print_info_arcs()

    def get_arc_by_id(self, id: int) -> Arc:

        if not isinstance(id, int):
            raise ValueError("maybe you meant 'get_arc_by_osm_id'?")

        if self.arcs[id].id == id:
            # all good
            return self.arcs[id]

        for pos, arc in enumerate(self.arcs):
            if arc.hash == id:
                return arc

    def compute_path_length(self, path, weight='length'):
        """
        Computes the length of a given path in a NetworkX graph.
        """
        length = 0
        for i in range(len(path) - 1):
            length += self.G[path[i]][path[i + 1]].get(weight, 1)  # Default weight is 1 if not specified
        return length

    def print_info_arcs(self):
        # Travel times and estimated lengths for used arcs (excluding dummies)
        travel_times_arcs = [arc.nominal_travel_time for arc in self.arcs if not arc.is_dummy]
        length_arcs_used = [t * (50 / 9) for t in travel_times_arcs]  # assuming 20 km/h

        # Real lengths from all arcs in the network
        arc_lengths_all = [data["length"] for _, _, data in self.G.edges(data=True) if "length" in data]

        # Stats preparation
        def safe_stats(values):
            return (
                len(values),
                mean(values),
                median(values),
                stdev(values) if len(values) > 1 else 0.0,
                min(values),
                max(values),
            )

        stats_used = safe_stats(length_arcs_used)
        stats_all = safe_stats(arc_lengths_all)

        # Table header
        print("\n" + "=" * 80)
        print(f"{'ARC LENGTH STATISTICS':^80}")
        print(f"{'(Used arcs at 20 km/h vs All arcs from graph)':^80}")
        print("=" * 80)
        print(f"{'Metric':<30} {'Used [m]':>20} {'All Arcs [m]':>20}")
        print("-" * 80)

        # Labels
        labels = ["Count", "Mean", "Median", "Standard Deviation", "Min", "Max"]
        for label, val_used, val_all in zip(labels, stats_used, stats_all):
            print(f"{label:<30} {val_used:>20.2f} {val_all:>20.2f}")

        print("=" * 80 + "\n")
