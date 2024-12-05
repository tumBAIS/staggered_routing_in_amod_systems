import contextily as ctx
import networkx as nx
import osmnx as osm
from matplotlib import pyplot as plt
from shapely import LineString, Point
from pathlib import Path
from collections.abc import Hashable
import utils.tools
from typing import Optional
import geopandas as gpd
import numpy as np
import matplotlib.cm as cm

WEB_MERCATOR_CRS = "EPSG:3857"


def keep_selected_highways(G):
    """
    Keeps only the edges in the graph that are classified as specific highway types:
    primary, secondary, tertiary, unclassified, and residential.

    Parameters:
    G (networkx.MultiDiGraph): The input graph with edges that contain a 'highway' attribute.

    Returns:
    networkx.MultiDiGraph: The modified graph with only selected highway types retained.
    """
    # Define allowed highway types
    allowed_highways = {
        'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential',
        'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', "living_street", "pedestrian"
    }
    # Identify edges to remove
    edges_to_remove = []
    for u, v, key, data in G.edges(keys=True, data=True):
        highway_attr = data.get('highway', None)

        # Check if the highway attribute matches any of the allowed types
        if isinstance(highway_attr, list):
            # If highway attribute is a list, check if any value in it is allowed
            if not any(h in allowed_highways for h in highway_attr):
                edges_to_remove.append((u, v, key))
        else:
            # If highway attribute is a string, check if it's allowed
            if highway_attr not in allowed_highways:
                edges_to_remove.append((u, v, key))

    # Remove the identified edges
    G.remove_edges_from(edges_to_remove)

    return G


def get_G_from_osm_place(place: str, path_to_G: Path) -> nx.MultiDiGraph:
    """Get G from OSM, and preprocess it to remove redundant arcs."""
    # Download 'drive' and 'drive_service' networks separately
    G = osm.graph_from_place(place, network_type="all")
    G = keep_selected_highways(G)
    _remove_parallel_edges(G)
    G = _extract_largest_strongly_connected_component(G)
    G = osm.project_graph(G, to_crs=WEB_MERCATOR_CRS)
    G = osm.consolidate_intersections(G, tolerance=20)
    _merge_arcs_by_degree_two_nodes(G)
    _add_extended_length_attribute(G)
    plot_real_world_G(G, path_to_G)
    utils.tools.serialize(G, path_to_G)
    return G


def get_southern_percentage_of_network(G: nx.MultiDiGraph, percentage: int, path_to_H: Path) -> nx.DiGraph:
    """Return the graph composed by the specified percentage of most-south nodes of G."""
    southern_nodes = _get_southern_nodes(G, percentage)
    subgraph = G.subgraph(southern_nodes).copy()

    # Remove dead ends until no more can be removed
    while True:
        dead_ends = [node for node in subgraph.nodes if subgraph.degree(node) < 2]
        if not dead_ends:
            break
        subgraph.remove_nodes_from(dead_ends)

    # Get the largest strongly connected component
    largest_scc = max(nx.strongly_connected_components(subgraph), key=len)
    H = subgraph.subgraph(largest_scc).copy()
    _merge_arcs_by_degree_two_nodes(H)
    plot_real_world_G(H, path_to_H)
    utils.tools.serialize(H, path_to_H)
    return nx.DiGraph(H)


def _add_extended_length_attribute(G: nx.MultiDiGraph) -> None:
    """Add extended length edge attribute: used to compute alterantive shortest paths."""
    # Iterate over all edges to copy the 'length' attribute to 'extended_length'
    for u, v, data in G.edges(data=True):
        if 'length' in data:
            data['extended_length'] = data['length']


def _remove_parallel_edges(G: nx.MultiDiGraph) -> None:
    """
    Remove parallel edges from a MultiDiGraph, keeping only one edge (e.g., the shortest) between any pair of nodes.
    """

    edges_to_remove = []

    # Iterate through all edges in the MultiDiGraph
    for u, v in G.edges():
        # Get all parallel edges between node pair (u, v)
        parallel_edges = list(G[u][v].keys())

        if len(parallel_edges) > 1:
            # Select the edge to keep as the one with the minimum length
            min_edge_key = min(parallel_edges, key=lambda k: G[u][v][k]['length'])

            # Mark all other parallel edges for removal
            for key in parallel_edges:
                if key != min_edge_key:
                    edges_to_remove.append((u, v, key))

    # Remove marked parallel edges
    G.remove_edges_from(edges_to_remove)


def _remove_motorways_and_connecting_arcs(G: nx.MultiDiGraph) -> None:
    """
    Removes motorway edges and edges that connect the network to motorways from the given OSMnx graph.
    """
    # Identify motorway edges
    motorway_edges = [(u, v, k) for u, v, k, data in G.edges(keys=True, data=True) if data.get('highway') == 'motorway']

    # Remove motorway edges
    G.remove_edges_from(motorway_edges)

    # Identify nodes that were connected to motorways
    motorway_nodes = {u for u, v, k in motorway_edges} | {v for u, v, k in motorway_edges}

    # Identify and remove edges connected to motorway nodes
    connecting_edges = [(u, v, k) for u, v, k in G.edges(keys=True) if u in motorway_nodes or v in motorway_nodes]
    G.remove_edges_from(connecting_edges)


def _merge_arcs_by_degree_two_nodes(G: nx.MultiDiGraph):
    """
    Repeatedly merges arcs connected by degree two nodes in a network multidigraph by replacing them with a single arc,
    ensuring that the geometry of the new arc is correctly formed.
    """

    while True:
        degree_two_nodes = [node for node in G if G.degree(node) == 2]
        if not degree_two_nodes:
            break

        for node in degree_two_nodes:
            preds, succs = list(G.predecessors(node)), list(G.successors(node))
            if len(preds) != 1 or len(succs) != 1:
                continue
            u, v = preds[0], succs[0]
            edge_data_in, edge_data_out = G.get_edge_data(u, node), G.get_edge_data(node, v)

            for key_in, attr_in in edge_data_in.items():
                for key_out, attr_out in edge_data_out.items():
                    combined_attr = {**attr_in, **attr_out}
                    if 'geometry' in attr_in and 'geometry' in attr_out:
                        combined_attr['geometry'] = LineString(
                            list(attr_in['geometry'].coords) + list(attr_out['geometry'].coords))
                    G.add_edge(u, v, **combined_attr)

            G.remove_node(node)


def _extract_largest_strongly_connected_component(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Extract the largest strongly connected component from a directed graph."""
    # Find strongly connected components (SCCs) and sort them by size in descending order
    sccs = sorted(nx.strongly_connected_components(G), key=len, reverse=True)
    # Get the largest SCC
    largest_scc_nodes = sccs[0]
    # Create a subgraph of the graph containing only the nodes in the largest SCC
    largest_scc = G.subgraph(largest_scc_nodes).copy()

    return largest_scc


def plot_real_world_G(G: nx.MultiDiGraph, path_to_G: Path, paths: Optional[list[list[int]]] = None,
                      plot_map: bool = True) -> None:
    """Plot real world graph on map."""
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(12, 12))

    # Plot the edges
    edges = osm.graph_to_gdfs(G, nodes=False)
    nodes = osm.graph_to_gdfs(G, edges=False)
    edges.plot(ax=ax, linewidth=1, edgecolor='dimgray')
    nodes.plot(ax=ax, markersize=2, color='red', zorder=10, alpha=0.6)

    if plot_map:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.PositronNoLabels, zoom=14)

    # Plot paths
    if paths is not None:
        _plot_paths(G, ax, paths, edges)

    # Save the figure as a JPEG file
    plt.axis("off")
    name = "network" if paths is None else "network_with_paths"
    fig.savefig(path_to_G.parent / f"{name}.jpeg", dpi=300, bbox_inches='tight', pad_inches=0.1)
    fig.savefig(path_to_G.parent / f"{name}.pdf", dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)


def _plot_paths(G, ax: plt.Axes, paths: list[list[int]], edges: gpd.GeoDataFrame):
    # Define colors and linewidths
    colors = cm.viridis(np.linspace(0, 1, len(paths)))
    max_linewidth = 6
    min_linewidth = 2
    linewidths = np.linspace(max_linewidth, min_linewidth, len(paths))

    # Plot the paths
    for idx, path in enumerate(paths):
        path_edges = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            # Collect all edges between u and v (considering MultiDiGraph)
            for key in G[u][v]:
                edge_data = G.get_edge_data(u, v, key)
                path_edges.append(edge_data['geometry'])

        # Create a GeoDataFrame for the path edges
        if path_edges:
            path_line = LineString([point for line in path_edges for point in line.coords])
            path_gdf = gpd.GeoDataFrame(geometry=[path_line], crs=edges.crs)
            path_gdf.plot(ax=ax, linewidth=linewidths[idx], edgecolor=colors[idx], zorder=5)

        # Plot the OD pairs
        origin_node = path[0]
        destination_node = path[-1]
        origin_point = Point((G.nodes[origin_node]['x'], G.nodes[origin_node]['y']))
        destination_point = Point((G.nodes[destination_node]['x'], G.nodes[destination_node]['y']))
        od_gdf = gpd.GeoDataFrame(geometry=[origin_point, destination_point], crs=edges.crs)
        od_gdf.plot(ax=ax, markersize=80, color=['blue', 'orange'], zorder=6, marker='o')


def _get_southern_nodes(G: nx.MultiDiGraph, percentage: int) -> list[Hashable]:
    """Return the specified percentage of southern nodes of G."""
    sorted_nodes = sorted(G.nodes(data=True), key=lambda x: x[1]['y'])
    num_nodes_to_keep = int(len(sorted_nodes) * (percentage / 100))
    return [node for node, _ in sorted_nodes[:num_nodes_to_keep]]
