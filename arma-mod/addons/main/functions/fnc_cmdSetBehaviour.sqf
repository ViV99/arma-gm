/*
  fnc_cmdSetBehaviour.sqf
  Execute set_behaviour command: change AI behavior and combat mode.
  params: hashmap with keys: unit, behaviour, combat_mode
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _behaviour = _p getOrDefault ["behaviour", "aware"];
private _combatMode = _p getOrDefault ["combat_mode", "yellow"];

private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM set_behaviour: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Map to Arma behavior strings
private _armaBehaviour = switch (toLower _behaviour) do {
    case "safe":    { "SAFE" };
    case "aware":   { "AWARE" };
    case "combat":  { "COMBAT" };
    case "stealth": { "STEALTH" };
    default         { "AWARE" };
};

// Map to Arma combat mode strings
private _armaCombatMode = switch (toLower _combatMode) do {
    case "blue":   { "BLUE" };    // Never fire
    case "green":  { "GREEN" };   // Hold fire
    case "white":  { "WHITE" };   // Return fire
    case "yellow": { "YELLOW" };  // Fire at will
    case "red":    { "RED" };     // Engage at will
    default        { "YELLOW" };
};

_grp setBehaviour _armaBehaviour;
_grp setCombatMode _armaCombatMode;

["ArmaGM: %1 behaviour=%2 combatMode=%3", _unitId, _armaBehaviour, _armaCombatMode] call BIS_fnc_logFormat;
