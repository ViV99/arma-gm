from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UnitType(str, Enum):
    INFANTRY_SQUAD = "infantry_squad"
    MOTORIZED = "motorized"
    ARMOR = "armor"
    STATIC = "static"


class UnitStatus(str, Enum):
    DEFENDING = "defending"
    MOVING = "moving"
    COMBAT = "combat"
    RETREATING = "retreating"
    IDLE = "idle"
    PATROLLING = "patrolling"


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObjectiveStatus(str, Enum):
    HELD = "held"
    CONTESTED = "contested"
    LOST = "lost"


class PacingPhase(str, Enum):
    CALM = "calm"
    BUILD_UP = "build_up"
    PEAK = "peak"
    RELAX = "relax"


class EventType(str, Enum):
    UNIT_KILLED = "unit_killed"
    UNIT_DAMAGED = "unit_damaged"
    CONTACT_NEW = "contact_new"
    CONTACT_LOST = "contact_lost"
    OBJECTIVE_CHANGED = "objective_changed"
    FORTIFICATION_BUILT = "fortification_built"


class FriendlyUnit(BaseModel):
    id: str
    type: UnitType
    size: int = Field(ge=1)
    position: str  # graph node ID
    status: UnitStatus
    health: float = Field(ge=0.0, le=1.0)
    ammo: float = Field(ge=0.0, le=1.0)
    current_task: str = ""


class EnemyContact(BaseModel):
    id: str
    type: str  # infantry/vehicle/armor/unknown
    estimated_size: str  # fire_team/squad/platoon/unknown
    position: str  # graph node ID
    confidence: float = Field(ge=0.0, le=1.0)
    direction: str = ""  # approaching/retreating/stationary/flanking
    last_seen: float | None = None


class Objective(BaseModel):
    id: str
    status: ObjectiveStatus
    threat_level: ThreatLevel
    graph_node: str


class GameEvent(BaseModel):
    type: EventType
    data: dict[str, Any] = {}
    timestamp: float | None = None


class ResourcePool(BaseModel):
    reserve_infantry: int = Field(ge=0, default=0)
    reserve_motorized: int = Field(ge=0, default=0)
    artillery_available: bool = True
    cas_available: bool = False


class PacingInfo(BaseModel):
    current_phase: PacingPhase = PacingPhase.CALM
    intensity: float = Field(ge=0.0, le=1.0, default=0.0)
    phase_ticks: int = Field(ge=0, default=0)


class GraphData(BaseModel):
    strategic: dict[str, Any] = {}
    tactical: dict[str, Any] = {}
    local: dict[str, Any] | None = None
    # Dynamic overrides sent by SQF: node_id -> {property: value}
    # e.g. {"agia_marina_warehouse": {"cover_quality": 0.2}}
    node_updates: dict[str, dict[str, Any]] = {}


class GameState(BaseModel):
    tick_id: int
    mission_time: float
    friendly_forces: list[FriendlyUnit] = []
    enemy_contacts: list[EnemyContact] = []
    objectives: list[Objective] = []
    events_since_last_tick: list[GameEvent] = []
    resources: ResourcePool = ResourcePool()
    graph: GraphData = GraphData()
    pacing: PacingInfo = PacingInfo()
