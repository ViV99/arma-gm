#!/usr/bin/env python3
"""Graph visualizer for Arma 3 GM map graphs.

Loads graph JSON from shared/maps/, draws nodes colored by type and edges
by road type using networkx + matplotlib.

Usage:
    python tools/graph_visualizer.py shared/maps/stratis/strategic_graph.json
    python tools/graph_visualizer.py shared/maps/stratis/tactical/agia_marina.json --output graph.png
"""

import argparse
import json
import sys

try:
    import matplotlib.pyplot as plt
    import networkx as nx
except ImportError:
    print("ERROR: networkx and matplotlib are required.")
    print("Install with: pip install networkx matplotlib")
    sys.exit(1)


# Node colors by type
NODE_COLORS = {
    "town": "#4488cc",
    "military": "#cc4444",
    "terrain": "#44aa44",
    "entry_point": "#dd8800",
    "landing_zone": "#9944cc",
    "intersection": "#4488cc",
    "landmark": "#ddaa00",
    "residential": "#5588bb",
    "approach": "#dd8800",
    "commercial": "#44aa88",
    "industrial": "#888844",
    "infrastructure": "#7788aa",
    "building": "#6688aa",
    "road": "#999999",
    "passage": "#aa8866",
    "elevated": "#cc6688",
    "open_area": "#66aa66",
    "cover": "#668844",
}
DEFAULT_NODE_COLOR = "#aaaaaa"

# Edge width by road type
EDGE_WIDTHS = {
    "main": 3.0,
    "secondary": 2.0,
    "dirt": 1.5,
    "path": 1.0,
    "none": 0.5,
}

EDGE_COLORS = {
    "main": "#cccc44",
    "secondary": "#aaaa66",
    "dirt": "#886644",
    "path": "#666644",
    "none": "#444444",
}


def load_graph(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_networkx_graph(data: dict):
    G = nx.Graph()
    positions = {}
    node_colors = []
    node_labels = {}

    for node in data.get("nodes", []):
        nid = node["id"]
        name = node.get("name", nid)
        ntype = node.get("type", "")
        pos = node.get("position", [0, 0, 0])

        G.add_node(nid)
        # Use x, z (horizontal plane) for 2D layout; ignore y (vertical in Arma)
        positions[nid] = (pos[0], pos[2])
        node_colors.append(NODE_COLORS.get(ntype, DEFAULT_NODE_COLOR))
        node_labels[nid] = name

    edge_widths = []
    edge_colors = []
    for edge in data.get("edges", []):
        fn = edge["from_node"]
        tn = edge["to_node"]
        rtype = edge.get("road_type", "none")
        G.add_edge(fn, tn, road_type=rtype, distance=edge.get("distance", 0))
        edge_widths.append(EDGE_WIDTHS.get(rtype, 0.5))
        edge_colors.append(EDGE_COLORS.get(rtype, "#444444"))

    return G, positions, node_colors, node_labels, edge_widths, edge_colors


def draw_graph(data: dict, output: str | None = None, title: str = ""):
    G, positions, node_colors, node_labels, edge_widths, edge_colors = build_networkx_graph(data)

    if not G.nodes:
        print("No nodes found in graph.")
        return

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    # Draw edges
    nx.draw_networkx_edges(
        G, positions, ax=ax,
        width=edge_widths,
        edge_color=edge_colors,
        alpha=0.7,
    )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, positions, ax=ax,
        node_color=node_colors,
        node_size=200,
        edgecolors="#ffffff",
        linewidths=0.5,
        alpha=0.9,
    )

    # Draw labels
    nx.draw_networkx_labels(
        G, positions, labels=node_labels, ax=ax,
        font_size=7,
        font_color="#e0e0e0",
        font_family="monospace",
    )

    graph_title = title or data.get("description", data.get("map", "Graph"))
    ax.set_title(graph_title, color="#00ff41", fontsize=12, fontfamily="monospace")
    ax.tick_params(colors="#666666")
    for spine in ax.spines.values():
        spine.set_color("#333333")

    # Legend for node types
    seen_types = set()
    legend_handles = []
    for node in data.get("nodes", []):
        ntype = node.get("type", "")
        if ntype and ntype not in seen_types:
            seen_types.add(ntype)
            color = NODE_COLORS.get(ntype, DEFAULT_NODE_COLOR)
            legend_handles.append(
                plt.Line2D([0], [0], marker="o", color="#1a1a2e",
                           markerfacecolor=color, markersize=8, label=ntype)
            )
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper left",
                  facecolor="#0d0d1a", edgecolor="#333333",
                  labelcolor="#a0d2a0", fontsize=8)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, facecolor=fig.get_facecolor())
        print(f"Saved to {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Visualize Arma 3 GM map graphs")
    parser.add_argument("graph_file", help="Path to graph JSON file")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PNG file (displays interactively if omitted)")
    parser.add_argument("--title", "-t", type=str, default="",
                        help="Custom graph title")
    args = parser.parse_args()

    data = load_graph(args.graph_file)
    draw_graph(data, output=args.output, title=args.title)


if __name__ == "__main__":
    main()
