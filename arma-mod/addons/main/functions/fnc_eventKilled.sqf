/*
  fnc_eventKilled.sqf
  Handle unit killed event. Updates contact information.
  Called from init.sqf EntityKilled handler.
  params: ["_unit", "_killer"]
*/

params ["_unit", "_killer"];

// Log kill event - already handled in init.sqf EntityKilled EH
// This function can be used for additional logic (e.g., objective status update)

// Check if any objective zone is now undefended
{
    params ["_id", "_status", "_threat", "_node"];
    private _nodePos = [_node] call ArmaGM_fnc_getNodePos;
    private _nearbyFriendly = {
        alive _x && side _x == east && _x distance _nodePos < 100
    } count allUnits;

    if (_nearbyFriendly == 0 && _status == "held") then {
        // Update objective to contested
        private _idx = _forEachIndex;
        ArmaGM_objectives set [_idx, [_id, "contested", "high", _node]];
        ["ArmaGM: Objective %1 now contested (no defenders nearby)", _id] call BIS_fnc_logFormat;
    };
} forEach ArmaGM_objectives;
