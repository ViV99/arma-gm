/*
  fnc_cmdPositionSquad.sqf
  Execute position_squad command: move group to location with defensive behavior.
  params: hashmap with keys: unit, location, task, sector
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _node = _p getOrDefault ["location", ""];
private _task = _p getOrDefault ["task", "defend"];
private _sector = _p getOrDefault ["sector", "N"];

private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM position_squad: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

private _targetPos = [_node] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM position_squad: node '%1' not found", _node] call BIS_fnc_logFormat;
};

// Clear waypoints, set hold position
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_targetPos, 0];
_wp setWaypointType "HOLD";
_wp setWaypointSpeed "NORMAL";
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointCompletionRadius 15;

// Set formation direction based on sector
private _dirMap = ["N","NE","E","SE","S","SW","W","NW"];
private _dirIdx = _dirMap find _sector;
if (_dirIdx >= 0) then {
    _grp setFormDir (_dirIdx * 45);
};

_grp setVariable ["ArmaGM_status", "defending"];
_grp setVariable ["ArmaGM_task", format ["%1 at %2", _task, _node]];

["ArmaGM: %1 defending %2, facing %3", _unitId, _node, _sector] call BIS_fnc_logFormat;
