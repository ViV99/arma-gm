import argparse
import logging
from pathlib import Path

import uvicorn

from gm_server.config import load_config
from gm_server.llm.client import LLMClient
from gm_server.llm.prompt_builder import PromptBuilder
from gm_server.logic.state_manager import StateManager
from gm_server.logic.pacing import PacingFSM
from gm_server.logic.validator import Validator
from gm_server.logic.decision_loop import DecisionLoop
from gm_server.graph.model import MapGraph
from gm_server.graph.context_builder import ContextBuilder
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

    # Load graphs
    maps_dir = project_root / config.maps_dir
    strategic_graph = MapGraph.load_from_json(maps_dir / "stratis" / "strategic_graph.json")
    logger.info(
        "Loaded strategic graph: %d nodes, %d edges",
        len(strategic_graph.nodes),
        len(strategic_graph.edges),
    )

    tactical_graphs: dict[str, MapGraph] = {}
    tactical_dir = maps_dir / "stratis" / "tactical"
    if tactical_dir.exists():
        for f in tactical_dir.glob("*.json"):
            graph = MapGraph.load_from_json(f)
            tactical_graphs[f.stem] = graph
            logger.info("Loaded tactical graph '%s': %d nodes", f.stem, len(graph.nodes))

    # Build combined graph for validator (strategic + all tactical)
    combined_graph = _build_combined_graph(strategic_graph, tactical_graphs)

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

    validator = Validator(state_manager, combined_graph, config.game.anti_thrash_ticks)

    context_builder = ContextBuilder(strategic_graph, tactical_graphs)

    decision_loop = DecisionLoop(
        llm_client=llm_client,
        prompt_builder=prompt_builder,
        state_manager=state_manager,
        validator=validator,
        pacing=pacing,
        context_builder=context_builder,
    )

    # Create and run app
    app = create_app(decision_loop, state_manager)

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


def _build_combined_graph(strategic: MapGraph, tactical: dict[str, MapGraph]) -> MapGraph:
    """Merge strategic and tactical graphs for validation."""
    combined = MapGraph(
        nodes=dict(strategic.nodes),
        edges=list(strategic.edges),
    )
    for tac_graph in tactical.values():
        combined.nodes.update(tac_graph.nodes)
        combined.edges.extend(tac_graph.edges)
    return combined


if __name__ == "__main__":
    main()
