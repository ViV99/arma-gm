/*
  fnc_init.sqf
  Pre-initialization: register ExtensionCallback EH, configure extension, start tick.
  Called automatically via CfgFunctions preInit = 1.
*/

// Only run on server
if (!isServer) exitWith {};

// Global state
ArmaGM_tickId = 0;
ArmaGM_events = [];        // Accumulated events since last tick
ArmaGM_chunkBuffer = [];   // For chunked responses
ArmaGM_chunkTotal = 0;
ArmaGM_groups = [];        // [[group_id, group], ...] - managed OPFOR groups
ArmaGM_objectives = [];    // [[obj_id, status, threat_level, node_id], ...]
ArmaGM_contacts = [];      // [[contact_id, type, est_size, node, confidence, direction, last_seen], ...]
ArmaGM_intelNode = "";     // Node requested for L2 extraction (cleared after each tick)
ArmaGM_nodeUpdates = createHashMap; // Dynamic node property overrides

// Configure extension server URL (can be overridden before init)
private _serverUrl = if (isNil "ArmaGM_serverUrl") then { "http://127.0.0.1:8080" } else { ArmaGM_serverUrl };
"ArmaGM" callExtension ["config", [_serverUrl]];

// Register ExtensionCallback handler
addMissionEventHandler ["ExtensionCallback", {
    params ["_name", "_function", "_data"];
    if (_name != "ArmaGM") exitWith {};
    if (!isServer) exitWith {};
    [_function, _data] call ArmaGM_fnc_receiveCommands;
}];

// Register EntityKilled EH: track unit casualties and building destruction
addMissionEventHandler ["EntityKilled", {
    params ["_entity", "_killer"];
    if (!isServer) exitWith {};

    if (_entity isKindOf "Man") then {
        // Find which ArmaGM group this unit belonged to
        private _grpId = "";
        {
            params ["_id", "_grp"];
            if (_entity in units _grp) exitWith { _grpId = _id };
        } forEach ArmaGM_groups;

        if (_grpId != "") then {
            ArmaGM_events pushBack [
                "unit_killed",
                format ['{"group":"%1","casualties":1}', _grpId],
                time
            ];
        };
    };

    // Building destroyed: downgrade cover quality of nearest node
    if (_entity isKindOf "Building") then {
        private _bPos = getPosATL _entity;
        private _nearNode = [_bPos] call ArmaGM_fnc_nearestNode;
        if (_nearNode != "unknown") then {
            // Degrade cover (destroyed building = less cover)
            private _existingUpdates = ArmaGM_nodeUpdates getOrDefault [_nearNode, createHashMap];
            private _currentCover = _existingUpdates getOrDefault ["cover_quality", 0.7];
            private _newCover = (_currentCover - 0.2) max 0.1;
            [_nearNode, "cover_quality", _newCover] call ArmaGM_fnc_graphUpdate;

            ArmaGM_events pushBack [
                "fortification_built",
                format ['{"node":"%1","change":"building_destroyed","cover_quality":%2}', _nearNode, _newCover toFixed 2],
                time
            ];
        };
    };
}];

// Start tick scheduler
[] spawn ArmaGM_fnc_tick;

["ArmaGM initialized. Tick interval: 15s, Server: %1", _serverUrl] call BIS_fnc_logFormat;
