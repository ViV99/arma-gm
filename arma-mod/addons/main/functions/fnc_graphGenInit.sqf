/*
  fnc_graphGenInit.sqf
  Orchestrator for automatic graph generation.
  Checks server cache first; if not cached, generates road network + L0 + L1 graphs.
  Sets ArmaGM_graphReady = true when done.
*/

if (!isServer) exitWith {};

["ArmaGM graphGenInit: Starting graph generation for %1", worldName] call BIS_fnc_logFormat;

// 1. Check cache
ArmaGM_cacheResult = "";
"ArmaGM" callExtension ["check_cache", [worldName]];

// Wait for cache callback (up to 10s)
private _cacheTimeout = diag_tickTime + 10;
waitUntil { sleep 0.1; ArmaGM_cacheResult != "" || diag_tickTime > _cacheTimeout };

if (ArmaGM_cacheResult != "" && { ArmaGM_cacheResult != "miss" }) then {
    // Cache hit: parse response and populate node positions
    ["ArmaGM graphGenInit: Cache hit for %1, loading cached graphs", worldName] call BIS_fnc_logFormat;

    private _parsed = parseJson ArmaGM_cacheResult;
    if (!isNil "_parsed") then {
        private _nodes = _parsed getOrDefault ["nodes", []];
        {
            private _id = _x getOrDefault ["id", ""];
            private _pos = _x getOrDefault ["position", [0, 0, 0]];
            if (_id != "") then {
                ArmaGM_nodePositions pushBack [_id, [_pos select 0, _pos select 1]];
            };
        } forEach _nodes;

        ["ArmaGM graphGenInit: Loaded %1 node positions from cache", count ArmaGM_nodePositions] call BIS_fnc_logFormat;
        ArmaGM_graphReady = true;
    } else {
        ["ArmaGM graphGenInit: Failed to parse cache data, generating fresh"] call BIS_fnc_logFormat;
        ArmaGM_cacheResult = "miss";
    };
};

// 2. If not cached, generate graphs
if (!ArmaGM_graphReady) then {
    ["ArmaGM graphGenInit: No cache, generating graphs for %1", worldName] call BIS_fnc_logFormat;

    // Build road network (blocking)
    [] call ArmaGM_fnc_graphGenRoads;

    // Build strategic L0 graph (blocking, sends to server, populates ArmaGM_nodePositions)
    [] call ArmaGM_fnc_graphGenL0;

    ArmaGM_graphReady = true;
    ["ArmaGM graphGenInit: L0 complete, graph ready. Spawning L1 generators..."] call BIS_fnc_logFormat;

    // Spawn L1 tactical graphs for settlements in background
    private _l0Nodes = +ArmaGM_nodePositions;
    {
        _x params ["_nodeId", "_pos2d"];
        private _centerPos = [_pos2d select 0, _pos2d select 1, 0];

        // Check if this is a settlement (has buildings nearby)
        private _nearBuildings = count nearestTerrainObjects [_centerPos, ["HOUSE", "BUILDING"], 200];
        if (_nearBuildings >= 10) then {
            // Determine radius based on building density
            private _radius = if (_nearBuildings > 40) then { 300 } else { 200 };
            [_nodeId, _centerPos, _radius] spawn ArmaGM_fnc_graphGenL1;
        };
    } forEach _l0Nodes;
};

["ArmaGM graphGenInit: Complete. %1 node positions registered.", count ArmaGM_nodePositions] call BIS_fnc_logFormat;
