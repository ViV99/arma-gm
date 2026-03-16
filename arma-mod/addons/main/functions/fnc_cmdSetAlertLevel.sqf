/*
  fnc_cmdSetAlertLevel.sqf
  Execute set_alert_level command: change behaviour and combat mode for all active groups.
  params: hashmap with keys: level (str: "high"/"medium"/"low"/"normal")
*/

params ["_p"];

private _level = _p getOrDefault ["level", "normal"];

// Map alert level to behaviour and combat mode
private _behaviour = "";
private _combatMode = "";
switch (_level) do {
    case "high": {
        _behaviour  = "COMBAT";
        _combatMode = "RED";
    };
    case "medium": {
        _behaviour  = "AWARE";
        _combatMode = "YELLOW";
    };
    case "low": {
        _behaviour  = "AWARE";
        _combatMode = "GREEN";
    };
    default {
        // "normal" and anything else
        _behaviour  = "AWARE";
        _combatMode = "YELLOW";
    };
};

// Apply to all registered groups
{
    params ["_id", "_grp"];
    _grp setBehaviour _behaviour;
    _grp setCombatMode _combatMode;
} forEach ArmaGM_groups;

["ArmaGM: Alert level set to %1 (%2 / %3)", _level, _behaviour, _combatMode] call BIS_fnc_logFormat;
