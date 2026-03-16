import logging
from collections import deque
from dataclasses import dataclass, field

from gm_server.models.commands import Command
from gm_server.models.game_state import GameState, ResourcePool

logger = logging.getLogger(__name__)


@dataclass
class Order:
    command_type: str
    params: dict
    issued_tick: int
    status: str = "executing"  # executing, completed, failed


@dataclass
class UnitRecord:
    id: str
    type: str
    side: str = "OPFOR"
    size_initial: int = 8
    size_current: int = 8
    status: str = "idle"
    position_node: str = ""
    current_order: Order | None = None
    health_aggregate: float = 1.0
    ammo_aggregate: float = 1.0
    casualties_total: int = 0
    last_updated: float = 0.0


@dataclass
class ObjectiveRecord:
    id: str
    status: str = "held"
    threat_level: str = "low"
    graph_node: str = ""


@dataclass
class Directive:
    text: str
    priority: str = "normal"
    ttl_ticks: int = 10
    remaining_ticks: int = 10


@dataclass
class EventRecord:
    type: str
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class TickSummary:
    tick_id: int
    commands_issued: int = 0
    events_count: int = 0
    intensity: float = 0.0


@dataclass
class SessionState:
    units: dict[str, UnitRecord] = field(default_factory=dict)
    objectives: dict[str, ObjectiveRecord] = field(default_factory=dict)
    reserves: ResourcePool = field(default_factory=ResourcePool)
    directives: list[Directive] = field(default_factory=list)
    override_queue: list[Command] = field(default_factory=list)
    events: deque[EventRecord] = field(default_factory=lambda: deque(maxlen=50))
    tick_history: list[TickSummary] = field(default_factory=list)
    mission_time: float = 0.0
    current_tick: int = 0
    paused: bool = False


class StateManager:
    def __init__(self, max_events: int = 50, max_tick_history: int = 20):
        self.state = SessionState()
        self.state.events = deque(maxlen=max_events)
        self.max_tick_history = max_tick_history
        self.last_game_state: GameState | None = None

    def update_from_game_state(self, game_state: GameState) -> None:
        """Sync state with fresh data from Arma."""
        self.last_game_state = game_state
        self.state.mission_time = game_state.mission_time
        self.state.current_tick = game_state.tick_id

        # Update units from Arma data
        seen_ids = set()
        for unit in game_state.friendly_forces:
            seen_ids.add(unit.id)
            if unit.id in self.state.units:
                rec = self.state.units[unit.id]
                rec.size_current = unit.size
                rec.status = unit.status.value
                rec.position_node = unit.position
                rec.health_aggregate = unit.health
                rec.ammo_aggregate = unit.ammo
                rec.last_updated = game_state.mission_time
                # Detect completed orders
                if rec.current_order and rec.current_order.status == "executing":
                    if self._is_order_complete(rec):
                        rec.current_order.status = "completed"
                        logger.info(
                            "Order completed for %s: %s", unit.id, rec.current_order.command_type
                        )
                # Track casualties
                if unit.size < rec.size_current:
                    new_casualties = rec.size_current - unit.size
                    rec.casualties_total += new_casualties
                    rec.size_current = unit.size
            else:
                # New unit
                self.state.units[unit.id] = UnitRecord(
                    id=unit.id,
                    type=unit.type.value,
                    size_initial=unit.size,
                    size_current=unit.size,
                    status=unit.status.value,
                    position_node=unit.position,
                    health_aggregate=unit.health,
                    ammo_aggregate=unit.ammo,
                    last_updated=game_state.mission_time,
                )

        # Update objectives
        for obj in game_state.objectives:
            self.state.objectives[obj.id] = ObjectiveRecord(
                id=obj.id,
                status=obj.status.value,
                threat_level=obj.threat_level.value,
                graph_node=obj.graph_node,
            )

        # Update resources
        self.state.reserves = game_state.resources

        # Record events
        for event in game_state.events_since_last_tick:
            self.state.events.append(
                EventRecord(
                    type=event.type.value,
                    data=event.data,
                    timestamp=event.timestamp or game_state.mission_time,
                )
            )

    def _is_order_complete(self, unit: UnitRecord) -> bool:
        """Check if unit's current order is completed."""
        if not unit.current_order:
            return False
        order = unit.current_order
        # For movement orders, check if unit reached destination
        if order.command_type in ("move_squad", "move_vehicle", "retreat", "reinforce"):
            target = order.params.get("to") or order.params.get("fallback_position")
            if target and unit.position_node == target:
                return True
        # For position/fortify orders, check if unit is at location and defending
        if order.command_type in ("position_squad", "set_fortify"):
            target = order.params.get("location")
            if target and unit.position_node == target and unit.status in ("defending", "idle"):
                return True
        return False

    def apply_orders(self, commands: list[Command]) -> None:
        """Record validated commands as active orders on units."""
        for cmd in commands:
            unit_id = cmd.params.get("unit")
            if unit_id and unit_id in self.state.units:
                self.state.units[unit_id].current_order = Order(
                    command_type=cmd.type,
                    params=cmd.params,
                    issued_tick=self.state.current_tick,
                )
                logger.info("Applied order %s to %s", cmd.type, unit_id)

            # Handle resource deductions
            if cmd.type == "reinforce":
                reserve_type = cmd.params.get("from_reserve")
                if reserve_type == "infantry":
                    self.state.reserves.reserve_infantry = max(
                        0, self.state.reserves.reserve_infantry - 1
                    )
                elif reserve_type == "motorized":
                    self.state.reserves.reserve_motorized = max(
                        0, self.state.reserves.reserve_motorized - 1
                    )

        # Record tick summary
        self.state.tick_history.append(
            TickSummary(
                tick_id=self.state.current_tick,
                commands_issued=len(commands),
                events_count=len(list(self.state.events)),
            )
        )
        if len(self.state.tick_history) > self.max_tick_history:
            self.state.tick_history = self.state.tick_history[-self.max_tick_history :]

    def get_all_units(self) -> list[UnitRecord]:
        return list(self.state.units.values())

    def get_active_units(self) -> list[UnitRecord]:
        """Units that need new orders (no active order, or order completed/failed)."""
        return [
            u
            for u in self.state.units.values()
            if not u.current_order or u.current_order.status in ("completed", "failed")
        ]

    def add_directive(self, text: str, priority: str = "normal", ttl_ticks: int = 10) -> None:
        self.state.directives.append(
            Directive(
                text=text,
                priority=priority,
                ttl_ticks=ttl_ticks,
                remaining_ticks=ttl_ticks,
            )
        )
        logger.info("Directive added: '%s' (priority=%s, ttl=%d)", text, priority, ttl_ticks)

    def tick_directives(self) -> None:
        """Decrement TTL on directives, remove expired ones."""
        active = []
        for d in self.state.directives:
            d.remaining_ticks -= 1
            if d.remaining_ticks > 0:
                active.append(d)
            else:
                logger.info("Directive expired: '%s'", d.text)
        self.state.directives = active

    def add_override(self, commands: list[Command]) -> None:
        self.state.override_queue.extend(commands)
        logger.info("Added %d override commands", len(commands))

    def pop_overrides(self) -> list[Command]:
        overrides = list(self.state.override_queue)
        self.state.override_queue.clear()
        return overrides

    def get_state_summary(self) -> dict:
        """Summary for UI/logging."""
        return {
            "tick": self.state.current_tick,
            "mission_time": self.state.mission_time,
            "paused": self.state.paused,
            "units": [
                {
                    "id": u.id,
                    "type": u.type,
                    "status": u.status,
                    "position": u.position_node,
                    "size": f"{u.size_current}/{u.size_initial}",
                    "health": f"{u.health_aggregate:.0%}",
                    "ammo": f"{u.ammo_aggregate:.0%}",
                    "current_order": u.current_order.command_type if u.current_order else None,
                    "order_status": u.current_order.status if u.current_order else None,
                }
                for u in self.state.units.values()
            ],
            "objectives": [
                {"id": o.id, "status": o.status, "threat": o.threat_level, "node": o.graph_node}
                for o in self.state.objectives.values()
            ],
            "reserves": {
                "infantry": self.state.reserves.reserve_infantry,
                "motorized": self.state.reserves.reserve_motorized,
                "artillery": self.state.reserves.artillery_available,
                "cas": self.state.reserves.cas_available,
            },
            "directives": [
                {"text": d.text, "priority": d.priority, "remaining_ticks": d.remaining_ticks}
                for d in self.state.directives
            ],
            "override_queue_size": len(self.state.override_queue),
            "recent_events": [
                {"type": e.type, "data": e.data} for e in list(self.state.events)[-5:]
            ],
            "tick_history": [
                {"tick": t.tick_id, "commands": t.commands_issued}
                for t in self.state.tick_history[-10:]
            ],
        }
