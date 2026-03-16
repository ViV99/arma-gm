/*
  fnc_cmdSetFortify.sqf
  Execute set_fortify command: move group to location and fortify (prone, combat).
  params: hashmap with keys: unit (str), location (str)
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _location = _p getOrDefault ["location", ""];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM set_fortify: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Get node position
private _locPos = [_location] call ArmaGM_fnc_getNodePos;
if (_locPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM set_fortify: node '%1' not found", _location] call BIS_fnc_logFormat;
};

// Clear waypoints and set hold with combat behaviour
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_locPos, 0];
_wp setWaypointType "HOLD";
_wp setWaypointSpeed "NORMAL";
_wp setWaypointBehaviour "COMBAT";
_wp setWaypointCombatMode "RED";
_wp setWaypointCompletionRadius 15;

// Set all units prone
{ _x setUnitPos "DOWN" } forEach units _grp;

_grp setVariable ["ArmaGM_status", "fortified"];
_grp setVariable ["ArmaGM_task", format ["fortifying %1", _location]];

["ArmaGM: %1 fortifying %2", _unitId, _location] call BIS_fnc_logFormat;
