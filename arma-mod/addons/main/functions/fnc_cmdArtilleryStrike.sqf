/*
  fnc_cmdArtilleryStrike.sqf
  Execute artillery_strike command: fire off-map mortar at a target node.
  params: hashmap with keys: target_node (str), rounds (int, default 3)
*/

params ["_p"];

private _targetNode = _p getOrDefault ["target_node", ""];
private _rounds = _p getOrDefault ["rounds", 3];

// Check artillery availability (index 2 of ArmaGM_reserves)
private _reserves = if (isNil "ArmaGM_reserves") then { [2, 1, true, false] } else { ArmaGM_reserves };
if (!(_reserves select 2)) exitWith {
    ["ArmaGM artillery_strike: artillery not available", ""] call BIS_fnc_logFormat;
};

// Get target position
private _targetPos = [_targetNode] call ArmaGM_fnc_getNodePos;
if (_targetPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM artillery_strike: node '%1' not found", _targetNode] call BIS_fnc_logFormat;
};

// Spawn off-map mortar 2000m south of target
private _spawnPos = [(_targetPos select 0), (_targetPos select 1) - 2000, 0];
private _artUnit = "O_Mortar_01_F" createVehicle _spawnPos;

// Mark artillery unavailable immediately
_reserves set [2, false];
ArmaGM_reserves = _reserves;

// Fire in a spawned block, then clean up
[_artUnit, _targetPos, _rounds] spawn {
    params ["_art", "_tgt", "_n"];
    private _i = 0;
    while { _i < _n } do {
        _art doArtilleryFire [_tgt, "Sh_82mm_AMOS", 1];
        sleep 4;
        _i = _i + 1;
    };
    sleep 90;
    deleteVehicle _art;
};

// Record event — format: [type_string, data_json_string, timestamp]
ArmaGM_events pushBack [
    "fortification_built",
    format ['{"action":"artillery_strike","target_node":"%1","rounds":%2}', _targetNode, _rounds],
    time
];

["ArmaGM: Artillery strike on %1, %2 rounds", _targetNode, _rounds] call BIS_fnc_logFormat;
