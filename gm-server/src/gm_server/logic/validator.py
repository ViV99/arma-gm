import logging

from gm_server.graph.model import MapGraph
from gm_server.logic.state_manager import StateManager
from gm_server.models.commands import COMMAND_TYPES, Command

logger = logging.getLogger(__name__)

# Commands that target a specific unit
UNIT_COMMANDS = {
    "position_squad",
    "move_squad",
    "move_vehicle",
    "retreat",
    "set_behaviour",
    "despawn_group",
    "set_fortify",
    "set_patrol",
    "set_overwatch",
    "create_roadblock",
}

# Commands that target a graph node
NODE_COMMANDS = {
    "position_squad",
    "move_squad",
    "move_vehicle",
    "reinforce",
    "set_ambush",
    "artillery_strike",
    "retreat",
    "set_fortify",
    "set_overwatch",
    "request_intel",
    "create_roadblock",
    "call_cas",
}

# Commands that consume resources
RESOURCE_COMMANDS = {
    "reinforce": lambda p: (
        "reserve_infantry" if p.get("from_reserve") == "infantry" else "reserve_motorized"
    ),
    "artillery_strike": lambda p: "artillery",
    "call_cas": lambda p: "cas",
    "spawn_group": lambda p: "reserve_infantry",
}


class Validator:
    def __init__(
        self, state_manager: StateManager, graph: MapGraph, anti_thrash_ticks: int = 3
    ):
        self.state_manager = state_manager
        self.graph = graph
        self.anti_thrash_ticks = anti_thrash_ticks

    def validate(self, commands: list[Command]) -> list[Command]:
        """Validate commands and return only valid ones."""
        valid = []
        for cmd in commands:
            reasons = self._check_command(cmd)
            if reasons:
                logger.warning("Command rejected (%s): %s", cmd.type, "; ".join(reasons))
            else:
                valid.append(cmd)
        logger.info("Validated %d/%d commands", len(valid), len(commands))
        return valid

    def _check_command(self, cmd: Command) -> list[str]:
        """Return list of rejection reasons. Empty = valid."""
        reasons = []

        # Check command type is known
        if cmd.type not in COMMAND_TYPES:
            reasons.append(f"Unknown command type: {cmd.type}")
            return reasons

        # Validate params parse correctly
        try:
            cmd.validated_params()
        except Exception as e:
            reasons.append(f"Invalid params: {e}")
            return reasons

        # Check unit exists and is alive
        if cmd.type in UNIT_COMMANDS:
            unit_id = cmd.params.get("unit")
            if unit_id:
                unit = self.state_manager.state.units.get(unit_id)
                if not unit:
                    reasons.append(f"Unit '{unit_id}' does not exist")
                elif unit.size_current <= 0:
                    reasons.append(f"Unit '{unit_id}' is destroyed")

        # Check target nodes exist in graph
        if cmd.type in NODE_COMMANDS:
            node_fields = [
                "location",
                "to",
                "fallback_position",
                "target_node",
                "area",
                "trigger_zone",
            ]
            for node_field in node_fields:
                node_id = cmd.params.get(node_field)
                if node_id and not self.graph.node_exists(node_id):
                    reasons.append(f"Node '{node_id}' does not exist in graph")

            # Check route_nodes for patrol
            if cmd.type == "set_patrol":
                for node_id in cmd.params.get("route_nodes", []):
                    if not self.graph.node_exists(node_id):
                        reasons.append(f"Patrol node '{node_id}' does not exist")

        # Check resources
        if cmd.type in RESOURCE_COMMANDS:
            resource_check = RESOURCE_COMMANDS[cmd.type]
            resource_key = resource_check(cmd.params)
            if not self._has_resource(resource_key):
                reasons.append(f"Insufficient resource: {resource_key}")

        # Anti-thrashing check
        if cmd.type in UNIT_COMMANDS:
            unit_id = cmd.params.get("unit")
            if unit_id and not self._check_anti_thrash(unit_id, cmd):
                reasons.append(f"Anti-thrash: unit '{unit_id}' received order too recently")

        return reasons

    def _has_resource(self, resource_key: str) -> bool:
        r = self.state_manager.state.reserves
        if resource_key == "reserve_infantry":
            return r.reserve_infantry > 0
        elif resource_key == "reserve_motorized":
            return r.reserve_motorized > 0
        elif resource_key == "artillery":
            return r.artillery_available
        elif resource_key == "cas":
            return r.cas_available
        return True

    def _check_anti_thrash(self, unit_id: str, cmd: Command) -> bool:
        """Return True if command is allowed (not thrashing)."""
        unit = self.state_manager.state.units.get(unit_id)
        if not unit or not unit.current_order:
            return True  # No existing order, always allowed

        ticks_since = self.state_manager.state.current_tick - unit.current_order.issued_tick
        if ticks_since >= self.anti_thrash_ticks:
            return True  # Enough time has passed

        # Allow override if there's a significant reason
        # Check for new contacts or casualties in recent events
        recent_events = list(self.state_manager.state.events)[-5:]
        for event in recent_events:
            if event.type in ("contact_new", "unit_killed", "unit_damaged"):
                return True  # Significant event justifies change
        # Check for active directives
        if self.state_manager.state.directives:
            return True  # Operator directive overrides anti-thrash

        return False
