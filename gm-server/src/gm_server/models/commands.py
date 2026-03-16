from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# --- Param models for each command type ---


class PositionSquadParams(BaseModel):
    unit: str
    location: str  # graph node ID
    task: Literal["hold", "defend", "fortify"]
    sector: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


class MoveSquadParams(BaseModel):
    unit: str
    to: str  # graph node ID
    task: Literal["advance", "flank", "retreat", "reposition"]
    speed: Literal["slow", "normal", "full"] = "normal"


class MoveVehicleParams(BaseModel):
    unit: str
    to: str  # graph node ID
    task: Literal["transport", "support", "patrol"]


class ReinforceParams(BaseModel):
    from_reserve: Literal["infantry", "motorized"]
    to: str  # graph node ID
    composition: str  # e.g. "infantry_squad"
    route: str | None = None  # optional route node


class SetAmbushParams(BaseModel):
    units: list[str]
    location: str
    trigger_zone: str


class ArtilleryStrikeParams(BaseModel):
    target_node: str
    rounds: int = Field(ge=1, le=6)


class RetreatParams(BaseModel):
    unit: str
    fallback_position: str


class SetBehaviourParams(BaseModel):
    unit: str
    behaviour: Literal["safe", "aware", "combat", "stealth"]
    combat_mode: Literal["blue", "green", "white", "yellow", "red"]


class SpawnGroupParams(BaseModel):
    composition: str
    location: str
    task: str


class DespawnGroupParams(BaseModel):
    unit: str
    reason: str


class SetFortifyParams(BaseModel):
    unit: str
    location: str


class SetPatrolParams(BaseModel):
    unit: str
    route_nodes: list[str]


class SetOverwatchParams(BaseModel):
    unit: str
    location: str
    watch_sector: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


class RequestIntelParams(BaseModel):
    area: str  # graph node ID


class SetAlertLevelParams(BaseModel):
    level: Literal["green", "yellow", "orange", "red"]


class CreateRoadblockParams(BaseModel):
    location: str
    unit: str


class CallCasParams(BaseModel):
    target_node: str
    type: Literal["gun_run", "bomb", "rocket"]


class SetPriorityParams(BaseModel):
    objective: str
    priority: Literal["low", "normal", "high", "critical"]


# Map command type string to params model
COMMAND_PARAMS_MAP: dict[str, type[BaseModel]] = {
    "position_squad": PositionSquadParams,
    "move_squad": MoveSquadParams,
    "move_vehicle": MoveVehicleParams,
    "reinforce": ReinforceParams,
    "set_ambush": SetAmbushParams,
    "artillery_strike": ArtilleryStrikeParams,
    "retreat": RetreatParams,
    "set_behaviour": SetBehaviourParams,
    "spawn_group": SpawnGroupParams,
    "despawn_group": DespawnGroupParams,
    "set_fortify": SetFortifyParams,
    "set_patrol": SetPatrolParams,
    "set_overwatch": SetOverwatchParams,
    "request_intel": RequestIntelParams,
    "set_alert_level": SetAlertLevelParams,
    "create_roadblock": CreateRoadblockParams,
    "call_cas": CallCasParams,
    "set_priority": SetPriorityParams,
}

COMMAND_TYPES = list(COMMAND_PARAMS_MAP.keys())


class Command(BaseModel):
    type: str  # one of the 18 command types
    params: dict  # will be validated against the specific params model
    priority: Priority = Priority.NORMAL
    reasoning: str = ""

    def validated_params(self) -> BaseModel:
        """Validate and return typed params."""
        params_cls = COMMAND_PARAMS_MAP.get(self.type)
        if not params_cls:
            raise ValueError(f"Unknown command type: {self.type}")
        return params_cls(**self.params)


class TickResponse(BaseModel):
    tick_id: int
    commands: list[Command] = []
