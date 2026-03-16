/*
  setupObjectives.sqf
  Define mission objectives (control zones).
  Objectives are checked by trigger zones or manually updated.
*/

ArmaGM_setupObjectives = {
    // Format: [id, status, threat_level, node_id]
    ArmaGM_objectives = [
        ["obj_crossroad", "held", "medium", "agia_marina_crossroad"],
        ["obj_church",    "held", "low",    "agia_marina_church"],
        ["obj_warehouse", "held", "low",    "agia_marina_warehouse"]
    ];

    // Set up trigger-based status updates
    // Trigger 1: Crossroad (2300, 2600) radius 60m
    private _trigger1 = createTrigger ["EmptyDetector", [2300, 2600, 0]];
    _trigger1 setTriggerArea [60, 60, 0, false];
    _trigger1 setTriggerActivation ["WEST", "PRESENT", false];
    _trigger1 setTriggerStatements [
        "this",
        // Activation: BLUFOR entered zone -> contested
        "ArmaGM_objectives set [0, [""obj_crossroad"", ""contested"", ""high"", ""agia_marina_crossroad""]];",
        // Deactivation: BLUFOR left zone -> check if held
        "private _eastNear = {alive _x && side _x == east} count (nearestObjects [[2300,2600,0], [""Man""], 80]);
         private _newStatus = if (_eastNear > 0) then {""held""} else {""lost""};
         ArmaGM_objectives set [0, [""obj_crossroad"", _newStatus, ""medium"", ""agia_marina_crossroad""]];"
    ];

    ["ArmaGM: %1 objectives defined", count ArmaGM_objectives] call BIS_fnc_logFormat;
};
