from __future__ import annotations

import logging
from threading import Lock

from gm_server.graph.model import MapGraph

logger = logging.getLogger(__name__)


class GraphRegistry:
    """Dynamic, thread-safe storage for map graphs at all levels."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._strategic: MapGraph | None = None
        self._tactical: dict[str, MapGraph] = {}  # zone_id -> graph

    # -- Strategic (L0) --

    def set_strategic(self, graph: MapGraph) -> None:
        with self._lock:
            self._strategic = graph
        logger.info("Registry: strategic graph set (%d nodes)", len(graph.nodes))

    def get_strategic(self) -> MapGraph | None:
        with self._lock:
            return self._strategic

    # -- Tactical (L1) --

    def set_tactical(self, zone_id: str, graph: MapGraph) -> None:
        with self._lock:
            self._tactical[zone_id] = graph
        logger.info(
            "Registry: tactical graph '%s' set (%d nodes)", zone_id, len(graph.nodes)
        )

    def get_tactical(self, zone_id: str) -> MapGraph | None:
        with self._lock:
            return self._tactical.get(zone_id)

    def is_tactical_ready(self, zone_id: str) -> bool:
        with self._lock:
            return zone_id in self._tactical

    # -- Combined (for validator) --

    def get_combined(self) -> MapGraph:
        """Merge strategic + all tactical into one graph for validation."""
        with self._lock:
            nodes: dict = {}
            edges: list = []
            if self._strategic:
                nodes.update(self._strategic.nodes)
                edges.extend(self._strategic.edges)
            for tac in self._tactical.values():
                nodes.update(tac.nodes)
                edges.extend(tac.edges)
            return MapGraph(nodes=nodes, edges=edges)

    # -- Node positions (for SQF) --

    def get_all_node_positions(self) -> list[dict]:
        """Return [{"id": id, "position": [x, y]}, ...] for all known nodes."""
        with self._lock:
            result: list[dict] = []
            seen: set[str] = set()
            for source in [self._strategic, *self._tactical.values()]:
                if source is None:
                    continue
                for nid, node in source.nodes.items():
                    if nid not in seen:
                        seen.add(nid)
                        result.append({
                            "id": nid,
                            "position": [node.position[0], node.position[1]],
                        })
            return result
