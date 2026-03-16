/*
  fnc_cmdSetOverwatch.sqf
  Execute set_overwatch command: position group at location facing a given sector.
  params: hashmap with keys: unit (str), location (str), watch_sector (str, default "N")
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _location = _p getOrDefault ["location", ""];
private _watchSector = _p getOrDefault ["watch_sector", "N"];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM set_overwatch: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Get node position
private _locPos = [_location] call ArmaGM_fnc_getNodePos;
if (_locPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM set_overwatch: node '%1' not found", _location] call BIS_fnc_logFormat;
};

// Clear waypoints and set hold
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};
private _wp = _grp addWaypoint [_locPos, 0];
_wp setWaypointType "HOLD";
_wp setWaypointSpeed "NORMAL";
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointCompletionRadius 15;

// Set formation direction based on watch sector
private _dirMap = ["N","NE","E","SE","S","SW","W","NW"];
private _dirIdx = _dirMap find _watchSector;
if (_dirIdx >= 0) then {
    _grp setFormDir (_dirIdx * 45);
};

// Set all units standing for better line-of-sight
{ _x setUnitPos "UP" } forEach units _grp;

_grp setVariable ["ArmaGM_status", "overwatch"];
_grp setVariable ["ArmaGM_task", format ["overwatch at %1 facing %2", _location, _watchSector]];

["ArmaGM: %1 overwatch at %2 facing %3", _unitId, _location, _watchSector] call BIS_fnc_logFormat;
