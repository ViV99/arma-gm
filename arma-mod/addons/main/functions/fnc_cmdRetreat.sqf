/*
  fnc_cmdRetreat.sqf
  Execute retreat command: move unit to fallback position at full speed.
  params: hashmap with keys: unit, fallback_position
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _fallbackNode = _p getOrDefault ["fallback_position", ""];

private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM retreat: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

private _targetPos = [_fallbackNode] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM retreat: node '%1' not found", _fallbackNode] call BIS_fnc_logFormat;
};

while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_targetPos, 0];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed "FULL";
_wp setWaypointBehaviour "SAFE";
_wp setWaypointCombatMode "GREEN";
_wp setWaypointCompletionRadius 20;

_grp setVariable ["ArmaGM_status", "retreating"];
_grp setVariable ["ArmaGM_task", format ["retreating to %1", _fallbackNode]];

["ArmaGM: %1 retreating to %2", _unitId, _fallbackNode] call BIS_fnc_logFormat;
