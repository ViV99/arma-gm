/*
  endConditions.sqf
  Mission end conditions for the City Defense scenario.
  Run via initServer or spawned separately.
*/

ArmaGM_checkEndConditions = {
    // BLUFOR victory: all objectives captured (lost by OPFOR)
    private _lostCount = {(_x select 1) == "lost"} count ArmaGM_objectives;
    if (_lostCount >= count ArmaGM_objectives) then {
        ["end1", true] call BIS_fnc_endMission;
    };

    // OPFOR victory: all BLUFOR eliminated
    private _bluforAlive = {alive _x && side _x == west} count allUnits;
    if (_bluforAlive == 0 && time > 30) then {
        ["end2", true] call BIS_fnc_endMission;
    };
};

// Check every 30 seconds
[] spawn {
    while { true } do {
        sleep 30;
        [] call ArmaGM_checkEndConditions;
    };
};
