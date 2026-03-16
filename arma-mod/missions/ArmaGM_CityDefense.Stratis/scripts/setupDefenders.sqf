/*
  setupDefenders.sqf
  Spawn and register OPFOR defending groups for Agia Marina.
  Called from initServer.sqf.
  Note: in the actual mission, groups should be placed in the editor instead.
  This script creates them programmatically for testing.
*/

ArmaGM_setupDefenders = {
    ArmaGM_groups = [];
    ArmaGM_reserves = [2, 1, true, false]; // [infantry, motorized, artillery, cas]

    // Helper: spawn a group at position and register it
    private _fnc_spawnAndRegister = {
        params ["_id", "_pos", "_type", "_units", "_status"];
        private _grp = [_pos, east, _units] call BIS_fnc_spawnGroup;
        _grp setGroupId _id;
        _grp setVariable ["ArmaGM_status", _status];
        _grp setVariable ["ArmaGM_type", _type];
        _grp setVariable ["ArmaGM_task", ""];
        ArmaGM_groups pushBack [_id, _grp];
        _grp
    };

    // Alpha squad: crossroad defense
    [
        "grp_alpha_1",
        [2300, 2600, 0],
        "infantry_squad",
        ["O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F",
         "O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Rifleman_F"],
        "defending"
    ] call _fnc_spawnAndRegister;

    // Bravo squad: church/reserve
    [
        "grp_bravo_1",
        [2320, 2620, 0],
        "infantry_squad",
        ["O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F",
         "O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F"],
        "idle"
    ] call _fnc_spawnAndRegister;

    // Charlie squad: warehouse (western sector)
    [
        "grp_charlie_1",
        [2220, 2650, 0],
        "infantry_squad",
        ["O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F",
         "O_Soldier_F","O_Soldier_F","O_Soldier_F","O_Soldier_F"],
        "defending"
    ] call _fnc_spawnAndRegister;

    // Delta: overwatch tower
    [
        "grp_delta_1",
        [2360, 2660, 0],
        "infantry_squad",
        ["O_Sniper_F","O_Soldier_F","O_Soldier_F","O_Soldier_F"],
        "idle"
    ] call _fnc_spawnAndRegister;

    // Motor: motorized reaction force
    [
        "grp_motor_1",
        [2350, 2590, 0],
        "motorized",
        ["O_Soldier_F","O_Soldier_F","O_Soldier_F"],
        "idle"
    ] call _fnc_spawnAndRegister;

    // Set initial behaviors
    {
        params ["_id", "_grp"];
        _grp setBehaviour "AWARE";
        _grp setCombatMode "YELLOW";
        _grp setFormation "WEDGE";
    } forEach ArmaGM_groups;

    ["ArmaGM: %1 groups registered", count ArmaGM_groups] call BIS_fnc_logFormat;
};
