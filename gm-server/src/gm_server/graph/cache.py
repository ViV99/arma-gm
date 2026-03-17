from __future__ import annotations

import json
import logging
from pathlib import Path

from gm_server.graph.model import MapGraph

logger = logging.getLogger(__name__)

CACHE_VERSION = 1


class GraphCache:
    """Disk cache for generated map graphs."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def save(self, map_name: str, level: int, zone_id: str | None, graph: MapGraph) -> None:
        """Persist a graph to disk."""
        dest = self.cache_dir / map_name
        dest.mkdir(parents=True, exist_ok=True)

        if level == 0:
            filename = "l0_strategic.json"
        else:
            filename = f"l1_{zone_id}.json"

        data = graph.to_dict()
        data["level"] = level
        with open(dest / filename, "w") as f:
            json.dump(data, f, indent=2)

        # Write / update meta
        meta_path = dest / "_meta.json"
        with open(meta_path, "w") as f:
            json.dump({"version": CACHE_VERSION, "map": map_name}, f)

        logger.info("Cache: saved %s/%s", map_name, filename)

    def load_all(self, map_name: str) -> tuple[MapGraph | None, dict[str, MapGraph]]:
        """Load all cached graphs for a map.

        Returns (strategic_graph_or_None, {zone_id: tactical_graph}).
        """
        cache_map_dir = self.cache_dir / map_name
        meta_path = cache_map_dir / "_meta.json"
        if not meta_path.exists():
            return None, {}

        with open(meta_path) as f:
            meta = json.load(f)
        if meta.get("version") != CACHE_VERSION:
            logger.warning("Cache version mismatch for '%s', ignoring cache", map_name)
            return None, {}

        strategic: MapGraph | None = None
        tactical: dict[str, MapGraph] = {}

        l0_path = cache_map_dir / "l0_strategic.json"
        if l0_path.exists():
            strategic = MapGraph.load_from_json(l0_path)
            logger.info("Cache: loaded strategic graph (%d nodes)", len(strategic.nodes))

        for l1_file in cache_map_dir.glob("l1_*.json"):
            zone_id = l1_file.stem[3:]  # strip "l1_" prefix
            graph = MapGraph.load_from_json(l1_file)
            tactical[zone_id] = graph
            logger.info("Cache: loaded tactical graph '%s' (%d nodes)", zone_id, len(graph.nodes))

        return strategic, tactical

    def exists(self, map_name: str) -> bool:
        meta_path = self.cache_dir / map_name / "_meta.json"
        return meta_path.exists()
