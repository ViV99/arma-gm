/*
  fnc_cmdMoveSquad.sqf
  Execute move_squad command: move a group to a target node.
  params: hashmap with keys: unit, to, task, speed
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _targetNode = _p getOrDefault ["to", ""];
private _task = _p getOrDefault ["task", "reposition"];
private _speed = _p getOrDefault ["speed", "normal"];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM move_squad: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Find node position
private _targetPos = [_targetNode] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM move_squad: node '%1' not found", _targetNode] call BIS_fnc_logFormat;
};

// Set movement speed
private _armaSpeed = switch (_speed) do {
    case "slow": { "LIMITED" };
    case "full": { "FULL" };
    default { "NORMAL" };
};

// Clear existing waypoints and add move waypoint
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_targetPos, 0];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed _armaSpeed;
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointCompletionRadius 20;

// Update status variable
_grp setVariable ["ArmaGM_status", "moving"];
_grp setVariable ["ArmaGM_task", format ["moving to %1", _targetNode]];

["ArmaGM: %1 moving to %2 (%3)", _unitId, _targetNode, _task] call BIS_fnc_logFormat;
