from statistics import mean, median, stdev
import geopandas as gpd
import jsonpickle
import networkx as nx
import shapely as shp
from networkx.readwrite import json_graph
from shapely import Polygon

from problem.arc import Arc
from problem.parameters import InstanceParams
from utils.aliases import *


class Network:

    def __init__(self, instance_params: InstanceParams, G: Optional[nx.DiGraph] = None):
        self.instance_params = instance_params
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
        self.shortest_path_map = {}
        self.map_arc_trip_path_position = []

    def __str__(self):
        return f"{self.instance_params.network_name}_{len(self.G.nodes)}_nodes_{len(self.G.edges)}_edges"

    def __repr__(self):
        return f"{self.instance_params.network_name}_{len(self.G.nodes)}_nodes_{len(self.G.edges)}_edges"

    def set_map_arc_trip_path_position(self, trips) -> None:
        """Maps each arc to its trips and the positions of the arcs in the trip routes."""
        # Initialize a list of lists to store positions for each arc
        self.map_arc_trip_path_position = [[] for _ in self.arcs]

        # Iterate through each arc
        for arc in self.arcs:
            if arc.is_dummy:
                continue
            # Initialize a list for each arc to store positions for each trip route
            self.map_arc_trip_path_position[arc.id] = [[] for _ in trips.R]

            # Iterate through each trip that potentially uses this arc
            for trip in arc.trips_potentially_using_arc:
                # Initialize positions as -1 for each route in the trip
                positions_in_paths = [-1 for _ in trip.routes.P]

                # Iterate through each route in the trip
                for route in trip.routes.P:
                    try:
                        # Find the position of the current arc in the route's network path
                        position = route.network_path_ids.index(arc.id)
                        # Update the position for this route
                        positions_in_paths[route.id] = position
                    except ValueError:
                        # If the arc is not found in the network path, skip
                        continue

                # Store the positions for this trip in the arc's list
                self.map_arc_trip_path_position[arc.id][trip.id] = positions_in_paths

        return

    @property
    def polygon(self) -> Polygon:
        return self.gdf_nodes.unary_union.convex_hull

    @staticmethod
    def _deserialize(file_path) -> nx.DiGraph:
        """Function to _deserialize a NetworkX MultiDiGraph from a JSON file."""
        with open(file_path, 'r+') as _file:
            call_graph = json_graph.adjacency_graph(jsonpickle.decode(_file.read()), directed=True)
        return nx.DiGraph(call_graph)

    def _serialize(self, file_path: str) -> None:
        '''Function to serialize a NetworkX DiGraph to a JSON file.'''
        if not isinstance(self.G, nx.DiGraph):
            raise Exception('call_graph has be an instanceModule of networkx.DiGraph')

        with open(file_path, 'w+') as _file:
            _file.write(jsonpickle.encode(
                json_graph.adjacency_data(self.G))
            )

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

        return int(nearest_node['node'].iloc[0])

    def _get_gdf_nodes(self) -> gpd.GeoDataFrame:
        """ Convert NetworkX graph nodes to a list of dictionaries for GeoDataFrame """
        nodes = [{'node': node, 'geometry': shp.Point(data['x'], data['y'])} for node, data in self.G.nodes(data=True)]
        return gpd.GeoDataFrame(nodes, geometry='geometry')

    def add_arcs(self, trips, instance_params: InstanceParams):
        """
        Add both dummy arcs (for disjoint paths) and real arcs (from OSM data) to the internal lists.
        """
        # Get OSM arcs utilized by trips
        osm_arcs_utilized = trips.get_osm_arcs_utilized()

        # Add dummy arcs (one for each alternative path)
        for dummy_id in range(instance_params.num_alternative_paths):
            dummy_arc = Arc.create_dummy_arc(id=dummy_id)
            self.arcs.append(dummy_arc)
            self.travel_time_arcs.append(dummy_arc.nominal_travel_time)  # This will always be 0 for dummy arcs
            self.nominal_capacities_arcs.append(dummy_arc.nominal_capacity)  # This will always be 0 or 1 for dummy arcs

        # Add real arcs from OSM data, starting with an ID after the dummy arcs
        for id_offset, osm_arc_id in enumerate(osm_arcs_utilized, start=instance_params.num_alternative_paths):
            osm_arc_info = self.G.edges[osm_arc_id]  # Get OSM info from the graph
            arc = Arc(id=id_offset, osm_info=osm_arc_info)
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

    def is_arc_id_dummy(self, arc_id: int) -> bool:
        return self.arcs[arc_id].is_dummy

    def compute_path_length(self, path, weight='length'):
        """
        Computes the length of a given path in a NetworkX graph.
        """
        length = 0
        for i in range(len(path) - 1):
            length += self.G[path[i]][path[i + 1]].get(weight, 1)  # Default weight is 1 if not specified
        return length


    def print_info_arcs(self):
        travel_times_arcs = [arc.nominal_travel_time for arc in self.arcs if not arc.is_dummy]

        # Header
        print("\n" + "=" * 60)
        print(f"{'ARCS NOMINAL TRAVEL TIMES STATISTICS':^60}")
        print(f"{'(Values in seconds)':^60}")
        print("=" * 60 + "\n")

        # Statistics
        print(f"{'Count:':<30} {len(travel_times_arcs)}")
        print(f"{'Mean:':<30} {mean(travel_times_arcs):.2f}")
        print(f"{'Median:':<30} {median(travel_times_arcs):.2f}")
        print(f"{'Standard Deviation:':<30} {stdev(travel_times_arcs):.2f}")
        print(f"{'Min:':<30} {min(travel_times_arcs):.2f}")
        print(f"{'Max:':<30} {max(travel_times_arcs):.2f}")

        # Footer
        print("\n" + "=" * 60 + "\n")
