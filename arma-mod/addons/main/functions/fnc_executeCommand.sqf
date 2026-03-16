/*
  fnc_executeCommand.sqf
  Dispatch a command to the appropriate executor.
  params: ["_command", [], [{}]]  -- Arma hashmap from parseJson
*/

params ["_command"];

private _type = _command getOrDefault ["type", ""];
private _params = _command getOrDefault ["params", createHashMap];
private _reasoning = _command getOrDefault ["reasoning", ""];

["ArmaGM CMD [%1]: %2", _type, _reasoning] call BIS_fnc_logFormat;

switch (_type) do {
    case "move_squad":      { [_params] call ArmaGM_fnc_cmdMoveSquad };
    case "position_squad":  { [_params] call ArmaGM_fnc_cmdPositionSquad };
    case "set_behaviour":   { [_params] call ArmaGM_fnc_cmdSetBehaviour };
    case "reinforce":       { [_params] call ArmaGM_fnc_cmdReinforce };
    case "retreat":         { [_params] call ArmaGM_fnc_cmdRetreat };
    case "artillery_strike": { [_params] call ArmaGM_fnc_cmdArtilleryStrike };
    case "set_ambush":       { [_params] call ArmaGM_fnc_cmdSetAmbush };
    case "set_fortify":      { [_params] call ArmaGM_fnc_cmdSetFortify };
    case "set_patrol":       { [_params] call ArmaGM_fnc_cmdSetPatrol };
    case "set_overwatch":    { [_params] call ArmaGM_fnc_cmdSetOverwatch };
    case "spawn_group":      { [_params] call ArmaGM_fnc_cmdSpawnGroup };
    case "despawn_group":    { [_params] call ArmaGM_fnc_cmdDespawnGroup };
    case "create_roadblock": { [_params] call ArmaGM_fnc_cmdCreateRoadblock };
    case "call_cas":         { [_params] call ArmaGM_fnc_cmdCallCas };
    case "set_alert_level":  { [_params] call ArmaGM_fnc_cmdSetAlertLevel };
    case "set_priority":     { [_params] call ArmaGM_fnc_cmdSetPriority };
    case "request_intel": {
        // LLM requests L2 local graph for an area; extracted on next tick
        private _area = _params getOrDefault ["area", ""];
        if (_area != "") then {
            ArmaGM_intelNode = _area;
            ["ArmaGM: Intel requested for node '%1', L2 graph on next tick", _area] call BIS_fnc_logFormat;
        };
    };
    default {
        ["ArmaGM: Unhandled command type: %1", _type] call BIS_fnc_logFormat;
    };
};
