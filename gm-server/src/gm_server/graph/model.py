from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    name: str
    level: int = Field(default=0, ge=0, le=2)  # 0=strategic, 1=tactical, 2=local
    position: tuple[float, float, float]  # x, y, z
    elevation: float = 0.0
    properties: dict[str, Any] = {}
    # properties include: cover_quality, dominance, vehicle_access,
    # building_count, tactical_suitability (list)


class GraphEdge(BaseModel):
    from_node: str
    to_node: str
    distance: float  # meters
    bearing: float = 0.0  # degrees
    road_type: str = "none"  # main/secondary/dirt/path/none
    elevation_change: float = 0.0
    cover_rating: float = Field(ge=0.0, le=1.0, default=0.5)
    vehicle_traversable: bool = True


class MapGraph(BaseModel):
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.nodes

    def get_neighbors(self, node_id: str) -> list[str]:
        neighbors = []
        for edge in self.edges:
            if edge.from_node == node_id:
                neighbors.append(edge.to_node)
            elif edge.to_node == node_id:
                neighbors.append(edge.from_node)
        return neighbors

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.from_node == node_id or e.to_node == node_id]

    def get_subgraph(self, node_ids: set[str]) -> MapGraph:
        sub_nodes = {nid: n for nid, n in self.nodes.items() if nid in node_ids}
        sub_edges = [e for e in self.edges if e.from_node in node_ids and e.to_node in node_ids]
        return MapGraph(nodes=sub_nodes, edges=sub_edges)

    def with_updates(self, node_updates: dict[str, dict]) -> MapGraph:
        """Return a new MapGraph with dynamic property overrides applied to nodes."""
        if not node_updates:
            return self
        updated_nodes = {}
        for nid, node in self.nodes.items():
            if nid in node_updates:
                merged = {**node.properties, **node_updates[nid]}
                updated_nodes[nid] = node.model_copy(update={"properties": merged})
            else:
                updated_nodes[nid] = node
        return MapGraph(nodes=updated_nodes, edges=self.edges)

    @classmethod
    def from_dict(cls, data: dict) -> MapGraph:
        """Build MapGraph from a plain dict (e.g. from SQF JSON)."""
        default_level = data.get("level", 2)
        nodes = {}
        for node_data in data.get("nodes", []):
            if "level" not in node_data:
                node_data = {**node_data, "level": default_level}
            node = GraphNode(**node_data)
            nodes[node.id] = node
        edges = [GraphEdge(**e) for e in data.get("edges", [])]
        return cls(nodes=nodes, edges=edges)

    @classmethod
    def load_from_json(cls, path: Path) -> MapGraph:
        """Load graph from JSON file."""
        with open(path) as f:
            data = json.load(f)
        # Top-level level applies to all nodes that don't specify their own
        default_level = data.get("level", 0)
        nodes = {}
        for node_data in data.get("nodes", []):
            if "level" not in node_data:
                node_data = {**node_data, "level": default_level}
            node = GraphNode(**node_data)
            nodes[node.id] = node
        edges = [GraphEdge(**e) for e in data.get("edges", [])]
        return cls(nodes=nodes, edges=edges)
