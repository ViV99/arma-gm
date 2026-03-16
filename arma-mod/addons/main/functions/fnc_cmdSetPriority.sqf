/*
  fnc_cmdSetPriority.sqf
  Execute set_priority command: update the threat_level of an objective.
  params: hashmap with keys: objective (str), priority (str: "critical"/"high"/"medium"/"low")
*/

params ["_p"];

private _objectiveId = _p getOrDefault ["objective", ""];
private _priority = _p getOrDefault ["priority", "medium"];

// Map priority string to threat level value
private _newThreat = switch (_priority) do {
    case "critical": { "critical" };
    case "high":     { "high" };
    case "low":      { "low" };
    default          { "medium" };
};

// Find objective by id (first element of each entry)
private _found = false;
private _idx = 0;
{
    private _entry = _x;
    private _id = _entry select 0;
    if (_id == _objectiveId) exitWith {
        // Objective entry format: [id, status, threat_level, node]
        private _status = _entry select 1;
        private _node   = _entry select 3;
        ArmaGM_objectives set [_idx, [_id, _status, _newThreat, _node]];
        _found = true;
    };
    _idx = _idx + 1;
} forEach ArmaGM_objectives;

if (!_found) then {
    ["ArmaGM set_priority: objective '%1' not found", _objectiveId] call BIS_fnc_logFormat;
} else {
    ["ArmaGM: Priority of '%1' set to %2 (threat: %3)", _objectiveId, _priority, _newThreat] call BIS_fnc_logFormat;
};
