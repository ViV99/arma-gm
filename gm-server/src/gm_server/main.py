import argparse
import logging
from pathlib import Path

import uvicorn

from gm_server.config import load_config
from gm_server.graph.cache import GraphCache
from gm_server.graph.model import MapGraph
from gm_server.graph.registry import GraphRegistry
from gm_server.graph.context_builder import ContextBuilder
from gm_server.llm.client import LLMClient
from gm_server.llm.prompt_builder import PromptBuilder
from gm_server.logic.state_manager import StateManager
from gm_server.logic.pacing import PacingFSM
from gm_server.logic.validator import Validator
from gm_server.logic.decision_loop import DecisionLoop
from gm_server.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Arma 3 Game Master Server")
    parser.add_argument("--config", type=Path, default=None, help="Path to config YAML")
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    host = args.host or config.server.host
    port = args.port or config.server.port

    # Find project root (contains shared/ directory)
    project_root = _find_project_root()

    # Create registry and cache
    registry = GraphRegistry()
    cache_dir = project_root / "gm-server" / "cache"
    graph_cache = GraphCache(cache_dir)

    # Loading priority: cache -> static fallback JSON -> empty (wait for SQF)
    map_name = "stratis"
    loaded = False

    if graph_cache.exists(map_name):
        strategic, tactical = graph_cache.load_all(map_name)
        if strategic:
            registry.set_strategic(strategic)
            for zone_id, tac_graph in tactical.items():
                registry.set_tactical(zone_id, tac_graph)
            loaded = True
            logger.info("Loaded graphs from cache for '%s'", map_name)

    if not loaded:
        # Fallback: try static JSON files
        maps_dir = project_root / config.maps_dir
        strategic_path = maps_dir / map_name / "strategic_graph.json"
        if strategic_path.exists():
            strategic_graph = MapGraph.load_from_json(strategic_path)
            registry.set_strategic(strategic_graph)
            logger.info(
                "Loaded static strategic graph: %d nodes, %d edges",
                len(strategic_graph.nodes),
                len(strategic_graph.edges),
            )

            tactical_dir = maps_dir / map_name / "tactical"
            if tactical_dir.exists():
                for f in tactical_dir.glob("*.json"):
                    graph = MapGraph.load_from_json(f)
                    registry.set_tactical(f.stem, graph)
                    logger.info("Loaded static tactical graph '%s': %d nodes", f.stem, len(graph.nodes))
        else:
            logger.warning("No cached or static graphs found for '%s' -- waiting for SQF", map_name)

    # Initialize components
    llm_client = LLMClient(
        base_url=config.llm.base_url,
        model=config.llm.model,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        timeout=config.llm.timeout_seconds,
    )

    prompts_dir = project_root / config.prompts_dir
    prompt_builder = PromptBuilder(prompts_dir)

    state_manager = StateManager(
        max_events=config.game.max_events_buffer,
        max_tick_history=config.game.max_tick_history,
    )

    pacing = PacingFSM(
        calm_to_buildup=config.pacing.calm_to_buildup,
        buildup_to_peak=config.pacing.buildup_to_peak,
        peak_to_relax=config.pacing.peak_to_relax,
        relax_to_calm=config.pacing.relax_to_calm,
        peak_max_ticks=config.pacing.peak_max_ticks,
    )

    validator = Validator(state_manager, registry, config.game.anti_thrash_ticks)

    context_builder = ContextBuilder(registry)

    decision_loop = DecisionLoop(
        llm_client=llm_client,
        prompt_builder=prompt_builder,
        state_manager=state_manager,
        validator=validator,
        pacing=pacing,
        context_builder=context_builder,
    )

    # Create and run app
    app = create_app(decision_loop, state_manager, registry, graph_cache)

    logger.info("Starting GM Server on %s:%d (model=%s)", host, port, config.llm.model)
    uvicorn.run(app, host=host, port=port, log_level="info")


def _find_project_root() -> Path:
    """Find project root by looking for shared/ directory."""
    # Try relative to this file
    here = Path(__file__).resolve().parent
    for candidate in [here / "../../../..", here / "../../..", here / "../.."]:
        root = candidate.resolve()
        if (root / "shared").exists():
            return root
    # Fallback to cwd
    cwd = Path.cwd()
    if (cwd / "shared").exists():
        return cwd
    # Try parent dirs
    for parent in cwd.parents:
        if (parent / "shared").exists():
            return parent
    return cwd


if __name__ == "__main__":
    main()
