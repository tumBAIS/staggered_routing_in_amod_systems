import random

import networkx as nx
from shapely import LineString
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Optional
# import tikzplotlib
from utils.tools import serialize


def create_pigou_network(path_to_G: Path) -> nx.DiGraph:
    """Create graph with only two nodes and two paths"""
    G = nx.DiGraph()
    LENGTH_PATH_ONE, LENGTH_PATH_TWO = 20, 22  # meters

    # Define node positions
    node_positions = {"A": (0, 0), "B": (1, 1), "C": (1, 0), "D": (0, 1)}
    for node, pos in node_positions.items():
        G.add_node(node, x=pos[0], y=pos[1])

    # Define edges with weights and geometries
    edges = [("A", "D", LENGTH_PATH_ONE / 2), ("D", "B", LENGTH_PATH_ONE / 2),
             ("A", "C", LENGTH_PATH_TWO / 2), ("C", "B", LENGTH_PATH_TWO / 2)]

    for u, v, length in edges:
        line = LineString([node_positions[u], node_positions[v]])
        G.add_edge(u, v, length=length, extended_length=length, geometry=line)

    # Relabel nodes to start from 0
    mapping = {old_label: new_label for new_label, old_label in enumerate(G.nodes())}
    G = nx.relabel_nodes(G, mapping)

    plot_synthetic_network(G, path_to_G)
    serialize(G, path_to_G)

    return G


def generate_directed_lattice_graph(n: int, edge_length: float, path_to_G: Path) -> nx.DiGraph:
    """Generates a directed 2D lattice graph with n x n nodes and adds a 'length' attribute to edges."""
    G = nx.DiGraph()
    node_label = {(x, y): label for label, (x, y) in enumerate([(x, y) for y in range(n) for x in range(n)], start=1)}

    for (x, y), label in node_label.items():
        G.add_node(label, x=x, y=y)
        half_length_int = int(edge_length / 2)
        rand_len = edge_length + random.randint(-half_length_int, half_length_int)
        if x + 1 < n:
            G.add_edge(label, node_label[(x + 1, y)], length=rand_len, extended_length=rand_len,
                       geometry=LineString([(x, y), (x + 1, y)]))
        if y + 1 < n:
            G.add_edge(label, node_label[(x, y + 1)], length=rand_len, extended_length=rand_len,
                       geometry=LineString([(x, y), (x, y + 1)]))

    plot_synthetic_network(G, path_to_G)
    serialize(G, path_to_G)

    return G


def plot_synthetic_network(G: nx.DiGraph, path_to_G: Path, shortest_paths: Optional[list[list[int]]] = None) -> None:
    """Save visualization of G in path_to_G.
    :argument shortest_paths: if passed, plots shortest paths on figure"""
    fig, ax = plt.subplots(figsize=(10, 10))
    pos = {node: (data['x'], data['y']) for node, data in G.nodes(data=True)}

    # Draw edges and nodes
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowstyle='-|>', arrowsize=20)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="w", node_size=500, edgecolors="k")
    nx.draw_networkx_edge_labels(G, pos, ax=ax,
                                 edge_labels={(u, v): data['length'] for u, v, data in G.edges(data=True)})

    # Highlight shortest paths
    if shortest_paths:
        for i, path in enumerate(shortest_paths):
            nx.draw_networkx_edges(G, pos, ax=ax, edgelist=list(zip(path, path[1:])), edge_color="k", width=2,
                                   arrows=True, arrowstyle='-|>', arrowsize=20)

    ax.axis('off')
    fig.savefig(path_to_G.parent / "network.jpeg", dpi=300)
    # tikzplotlib.save(path_to_G.parent / "network.tex")
    plt.close(fig)
