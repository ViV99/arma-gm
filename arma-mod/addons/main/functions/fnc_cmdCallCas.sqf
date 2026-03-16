/*
  fnc_cmdCallCas.sqf
  Execute call_cas command: spawn a CAS aircraft to attack a target node.
  params: hashmap with keys: target_node (str), type (str: "gun_run"/"bomb", default "gun_run")
*/

params ["_p"];

private _targetNode = _p getOrDefault ["target_node", ""];
private _casType = _p getOrDefault ["type", "gun_run"];

// Check CAS availability (index 3 of ArmaGM_reserves)
private _reserves = if (isNil "ArmaGM_reserves") then { [2, 1, true, false] } else { ArmaGM_reserves };
if (!(_reserves select 3)) exitWith {
    ["ArmaGM call_cas: CAS not available", ""] call BIS_fnc_logFormat;
};

// Get target position
private _targetPos = [_targetNode] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM call_cas: node '%1' not found", _targetNode] call BIS_fnc_logFormat;
};

// Mark CAS unavailable immediately
_reserves set [3, false];
ArmaGM_reserves = _reserves;

// Spawn CAS aircraft 1500m west of target at 250m altitude
private _spawnOffset = [(_targetPos select 0) - 1500, (_targetPos select 1), 250];
private _casVehicle = "O_Plane_CAS_02_F" createVehicle _spawnOffset;
_casVehicle setVelocity [50, 0, 0];

// Create crew group and crew the vehicle
private _casGroup = createGroup east;
createVehicleCrew _casVehicle;

// Add SAD waypoint at target for attack run
private _wp = _casGroup addWaypoint [_targetPos, 0];
_wp setWaypointType "SAD";
_wp setWaypointSpeed "FULL";
_wp setWaypointBehaviour "COMBAT";
_wp setWaypointCombatMode "RED";
_wp setWaypointCompletionRadius 100;

// Clean up after attack window
[_casVehicle, _casGroup] spawn {
    params ["_v", "_g"];
    sleep 120;
    { deleteVehicle _x } forEach crew _v;
    deleteVehicle _v;
    deleteGroup _g;
};

// Record event — format: [type_string, data_json_string, timestamp]
ArmaGM_events pushBack [
    "fortification_built",
    format ['{"action":"call_cas","target_node":"%1","cas_type":"%2"}', _targetNode, _casType],
    time
];

["ArmaGM: CAS (%1) called on %2", _casType, _targetNode] call BIS_fnc_logFormat;
