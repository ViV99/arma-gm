/*
  fnc_cmdReinforce.sqf
  Execute reinforce command: spawn reserve unit group at a location.
  params: hashmap with keys: from_reserve, to, composition
*/

params ["_p"];

private _fromReserve = _p getOrDefault ["from_reserve", "infantry"];
private _toNode = _p getOrDefault ["to", ""];
private _composition = _p getOrDefault ["composition", "infantry_squad"];

private _targetPos = [_toNode] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM reinforce: node '%1' not found", _toNode] call BIS_fnc_logFormat;
};

// Check reserves
private _reserves = if (isNil "ArmaGM_reserves") then { [2, 1, true, false] } else { ArmaGM_reserves };
private _resIdx = if (_fromReserve == "infantry") then {0} else {1};
if ((_reserves select _resIdx) <= 0) exitWith {
    ["ArmaGM reinforce: no %1 reserves available", _fromReserve] call BIS_fnc_logFormat;
};

// Spawn group offset from target
private _spawnPos = _targetPos getPos [200, random 360];
private _unitTypes = ["O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F"];
private _grp = [_spawnPos, east, _unitTypes] call BIS_fnc_spawnGroup;

// Assign group ID
private _newId = format ["grp_reserve_%1", floor time];
_grp setVariable ["ArmaGM_status", "moving"];
_grp setVariable ["ArmaGM_type", if (_fromReserve == "motorized") then {"motorized"} else {"infantry_squad"}];
_grp setVariable ["ArmaGM_task", format ["reinforcing %1", _toNode]];

// Register in groups list
ArmaGM_groups pushBack [_newId, _grp];

// Deduct reserve
_reserves set [_resIdx, (_reserves select _resIdx) - 1];
ArmaGM_reserves = _reserves;

// Move to target
private _wp = _grp addWaypoint [_targetPos, 0];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed "FULL";
_wp setWaypointCompletionRadius 20;

["ArmaGM: Reinforcing %1 with %2 (new group: %3)", _toNode, _fromReserve, _newId] call BIS_fnc_logFormat;
