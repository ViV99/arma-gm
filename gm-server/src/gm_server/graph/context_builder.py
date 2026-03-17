from __future__ import annotations

import logging

from gm_server.graph.model import MapGraph
from gm_server.graph.registry import GraphRegistry
from gm_server.models.game_state import GameState

logger = logging.getLogger(__name__)


class ContextResult:
    def __init__(self) -> None:
        self.strategic: MapGraph | None = None
        self.tactical_zones: dict[str, MapGraph] = {}  # zone_name -> subgraph
        self.local: MapGraph | None = None


class ContextBuilder:
    MAX_TACTICAL_ZONES = 2

    def __init__(self, registry: GraphRegistry) -> None:
        self.registry = registry

    def build_context(
        self, game_state: GameState, active_zones: list[str] | None = None
    ) -> ContextResult:
        """Build graph context at appropriate detail levels."""
        result = ContextResult()

        # Apply dynamic node overrides from SQF
        node_updates = game_state.graph.node_updates
        strategic = self.registry.get_strategic()
        if strategic:
            result.strategic = strategic.with_updates(node_updates)

        # Determine which zones need tactical detail
        zones = active_zones or self._detect_active_zones(game_state)
        for zone_id in zones[: self.MAX_TACTICAL_ZONES]:
            tac = self.registry.get_tactical(zone_id)
            if tac:
                result.tactical_zones[zone_id] = tac.with_updates(node_updates)

        # Include L2 local graph if SQF sent one
        if game_state.graph.local:
            try:
                result.local = MapGraph.from_dict(game_state.graph.local)
                logger.debug("L2 local graph: %d nodes", len(result.local.nodes))
            except Exception:
                logger.warning("Failed to parse L2 local graph data", exc_info=True)

        return result

    def _detect_active_zones(self, game_state: GameState) -> list[str]:
        """Find zones with combat or nearby contacts."""
        active: set[str] = set()
        for contact in game_state.enemy_contacts:
            # Find which strategic node this contact is near
            node = self._find_strategic_zone(contact.position)
            if node:
                active.add(node)
        for obj in game_state.objectives:
            if obj.status == "contested" or obj.threat_level in ("high", "critical"):
                node = self._find_strategic_zone(obj.graph_node)
                if node:
                    active.add(node)
        return list(active)

    def _find_strategic_zone(self, node_id: str) -> str | None:
        """Map a tactical node to its parent strategic zone.

        Convention: tactical nodes are prefixed with strategic node id,
        e.g. "agia_marina_east" -> "agia_marina".
        """
        strategic = self.registry.get_strategic()
        if not strategic:
            return None
        for strategic_id in strategic.nodes:
            if node_id.startswith(strategic_id):
                return strategic_id
        # Fallback: check if it IS a strategic node
        if strategic.node_exists(node_id):
            return node_id
        return None
