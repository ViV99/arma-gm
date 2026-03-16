import logging
from pathlib import Path

from gm_server.graph.context_builder import ContextResult
from gm_server.graph.serializer import serialize_local, serialize_strategic, serialize_tactical
from gm_server.logic.state_manager import Directive, StateManager
from gm_server.models.game_state import PacingInfo

logger = logging.getLogger(__name__)


class PromptBuilder:
    def __init__(self, prompts_dir: Path):
        self.system_template = (prompts_dir / "system.txt").read_text()
        self.examples = (prompts_dir / "examples.txt").read_text()

    def build(
        self,
        state_manager: StateManager,
        graph_context: ContextResult,
        pacing_info: PacingInfo,
        directives: list[Directive],
    ) -> tuple[str, str]:
        """Build (system_prompt, user_prompt) for LLM."""
        system = self._build_system(pacing_info)
        user = self._build_user(state_manager, graph_context, directives)
        return system, user

    def _build_system(self, pacing: PacingInfo) -> str:
        """Build system prompt with pacing guidance."""
        guidance = {
            "calm": (
                "Prepare defenses and position forces. No immediate threat "
                "-- use this time to optimize positions."
            ),
            "build_up": (
                "Enemy approaching. Increase readiness, prepare ambushes, "
                "position reserves. Tension should build."
            ),
            "peak": (
                "Active combat. Commit reserves if needed, execute flanking "
                "maneuvers, use all available assets."
            ),
            "relax": (
                "Combat winding down. Allow breathing room, reposition survivors, "
                "consolidate defenses."
            ),
        }
        pacing_text = guidance.get(pacing.current_phase.value, "Maintain current posture.")

        system = self.system_template.replace("{pacing_guidance}", pacing_text)
        system = system.replace("{intensity}", f"{pacing.intensity:.1f}")
        system = system.replace("{phase}", pacing.current_phase.value.upper())
        return system

    def _build_user(
        self,
        state_manager: StateManager,
        graph_context: ContextResult,
        directives: list[Directive],
    ) -> str:
        """Build user prompt with current state."""
        sections = []

        # Directives (highest priority, shown first)
        for d in directives:
            sections.append(
                f"=== COMMANDER DIRECTIVE [{d.priority.upper()}] "
                f"(expires in {d.remaining_ticks} ticks) ===\n"
                f"{d.text}\nThis overrides your current plans."
            )

        # Graph context
        if graph_context.strategic:
            sections.append(serialize_strategic(graph_context.strategic))
        for zone_name, zone_graph in graph_context.tactical_zones.items():
            sections.append(serialize_tactical(zone_graph, zone_name))
        if graph_context.local:
            center = graph_context.local.nodes and next(iter(graph_context.local.nodes), "")
            center_node = graph_context.local.nodes.get(center, None)
            center_name = center_node.properties.get("center_node", center) if center_node else ""
            sections.append(serialize_local(graph_context.local, center_name))

        # Current forces
        sections.append(self._format_forces(state_manager))

        # Enemy contacts
        sections.append(self._format_contacts(state_manager))

        # Objectives
        sections.append(self._format_objectives(state_manager))

        # Recent events
        sections.append(self._format_events(state_manager))

        # Resources
        sections.append(self._format_resources(state_manager))

        # Few-shot examples (abbreviated)
        sections.append(f"\n{self.examples}")

        # Output instruction
        sections.append(
            "\nAnalyze the situation and issue commands. Respond with a JSON object:\n"
            '{"commands": [{"type": "...", "params": {...}, '
            '"priority": "...", "reasoning": "..."}]}'
        )

        return "\n\n".join(s for s in sections if s)

    def _format_forces(self, sm: StateManager) -> str:
        lines = ["=== YOUR FORCES ==="]
        for unit in sm.get_all_units():
            order_info = ""
            if unit.current_order and unit.current_order.status == "executing":
                order_info = (
                    f" [EXECUTING: {unit.current_order.command_type} "
                    f"since tick {unit.current_order.issued_tick}]"
                )
            lines.append(
                f"- {unit.id} ({unit.type}): {unit.size_current}/{unit.size_initial} troops, "
                f"at {unit.position_node}, status: {unit.status}, "
                f"health: {unit.health_aggregate:.0%}, ammo: {unit.ammo_aggregate:.0%}"
                f"{order_info}"
            )
        return "\n".join(lines)

    def _format_contacts(self, sm: StateManager) -> str:
        lines = ["=== ENEMY CONTACTS ==="]
        if not sm.last_game_state or not sm.last_game_state.enemy_contacts:
            lines.append("No confirmed contacts.")
            return "\n".join(lines)
        for c in sm.last_game_state.enemy_contacts:
            lines.append(
                f"- {c.id}: {c.type} ({c.estimated_size}), at {c.position}, "
                f"confidence: {c.confidence:.0%}, {c.direction}"
            )
        return "\n".join(lines)

    def _format_objectives(self, sm: StateManager) -> str:
        lines = ["=== OBJECTIVES ==="]
        for obj in sm.state.objectives.values():
            lines.append(
                f"- {obj.id}: {obj.status} (threat: {obj.threat_level}), node: {obj.graph_node}"
            )
        return "\n".join(lines)

    def _format_events(self, sm: StateManager) -> str:
        lines = ["=== RECENT EVENTS ==="]
        events = list(sm.state.events)[-10:]  # last 10
        if not events:
            lines.append("No recent events.")
            return "\n".join(lines)
        for ev in events:
            lines.append(f"- [{ev.type}] {ev.data}")
        return "\n".join(lines)

    def _format_resources(self, sm: StateManager) -> str:
        r = sm.state.reserves
        lines = ["=== AVAILABLE RESOURCES ==="]
        lines.append(f"- Reserve infantry squads: {r.reserve_infantry}")
        lines.append(f"- Reserve motorized: {r.reserve_motorized}")
        lines.append(f"- Artillery: {'AVAILABLE' if r.artillery_available else 'UNAVAILABLE'}")
        lines.append(
            f"- Close air support: {'AVAILABLE' if r.cas_available else 'UNAVAILABLE'}"
        )
        return "\n".join(lines)
