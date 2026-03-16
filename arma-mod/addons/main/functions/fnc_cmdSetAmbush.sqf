/*
  fnc_cmdSetAmbush.sqf
  Execute set_ambush command: move group to ambush position and hold.
  params: hashmap with keys: unit (str), location (str), trigger_zone (str, optional)
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _location = _p getOrDefault ["location", ""];
private _triggerZone = _p getOrDefault ["trigger_zone", ""];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM set_ambush: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Get node position
private _locPos = [_location] call ArmaGM_fnc_getNodePos;
if (_locPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM set_ambush: node '%1' not found", _location] call BIS_fnc_logFormat;
};

// Clear waypoints and add move waypoint with stealth
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_locPos, 0];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed "LIMITED";
_wp setWaypointBehaviour "STEALTH";
_wp setWaypointCombatMode "BLUE";
_wp setWaypointCompletionRadius 10;

// Configure all units to hold position and engage
{
    _x setUnitPos "MIDDLE";
    _x enableAI "TARGET";
    _x disableAI "MOVE";
} forEach units _grp;

_grp setVariable ["ArmaGM_status", "ambush"];
_grp setVariable ["ArmaGM_task", format ["ambush at %1", _location]];

["ArmaGM: %1 set to ambush at %2", _unitId, _location] call BIS_fnc_logFormat;
