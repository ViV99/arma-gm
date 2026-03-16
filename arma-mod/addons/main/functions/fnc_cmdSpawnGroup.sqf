/*
  fnc_cmdSpawnGroup.sqf
  Execute spawn_group command: create a new OPFOR group at a location.
  params: hashmap with keys: composition (str: "squad"/"fire_team"/"motorized"),
          location (str), task (str, default "defend")
*/

params ["_p"];

private _composition = _p getOrDefault ["composition", "squad"];
private _location = _p getOrDefault ["location", ""];
private _task = _p getOrDefault ["task", "defend"];

// Get node position
private _spawnPos = [_location] call ArmaGM_fnc_getNodePos;
if (_spawnPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM spawn_group: node '%1' not found", _location] call BIS_fnc_logFormat;
};

// Determine unit types by composition
private _unitTypes = [];
switch (_composition) do {
    case "fire_team": {
        _unitTypes = ["O_Soldier_F","O_Soldier_F","O_Soldier_AR_F","O_Soldier_GL_F"];
    };
    case "motorized": {
        _unitTypes = ["O_Soldier_F","O_Soldier_F","O_Soldier_F"];
    };
    default {
        // squad (8 units)
        _unitTypes = ["O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F",
                      "O_Soldier_AR_F","O_Soldier_GL_F","O_medic_F","O_Soldier_TL_F"];
    };
};

// Spawn group with small random offset around node pos
private _offsetPos = _spawnPos getPos [random 10, random 360];
private _grp = [_offsetPos, east, _unitTypes] call BIS_fnc_spawnGroup;

// Generate ID using current tick counter
private _newId = format ["grp_spawn_%1", ArmaGM_tickId];

_grp setVariable ["ArmaGM_id",     _newId];
_grp setVariable ["ArmaGM_type",   _composition];
_grp setVariable ["ArmaGM_status", "idle"];
_grp setVariable ["ArmaGM_task",   format ["%1 at %2", _task, _location]];

// Register in groups list
ArmaGM_groups pushBack [_newId, _grp];

// Add HOLD waypoint at location
private _wp = _grp addWaypoint [_spawnPos, 0];
_wp setWaypointType "HOLD";
_wp setWaypointSpeed "NORMAL";
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointCompletionRadius 20;

["ArmaGM: Spawned %1 '%2' at %3 (id: %4)", _composition, _task, _location, _newId] call BIS_fnc_logFormat;
