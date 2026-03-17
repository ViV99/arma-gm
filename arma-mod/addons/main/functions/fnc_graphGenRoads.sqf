/*
  fnc_graphGenRoads.sqf
  Builds road network data structures used by L0/L1 graph generators.
  Populates: ArmaGM_roadGraph, ArmaGM_roadInfo, ArmaGM_roadPositions
  Blocking call, runs on server only.
*/

if (!isServer) exitWith {};

private _startTime = diag_tickTime;
["ArmaGM graphGenRoads: Scanning road network..."] call BIS_fnc_logFormat;

// Get all road objects on the map
private _mapCenter = [worldSize / 2, worldSize / 2, 0];
private _searchRadius = worldSize * 0.71;
private _allRoads = nearestTerrainObjects [_mapCenter, ["ROAD", "MAIN ROAD", "TRACK"], _searchRadius, false, true];

["ArmaGM graphGenRoads: Found %1 road segments", count _allRoads] call BIS_fnc_logFormat;

// Build connectivity graph
ArmaGM_roadGraph = createHashMap;
ArmaGM_roadInfo = createHashMap;
ArmaGM_roadPositions = createHashMap;

{
    private _road = _x;

    // Connectivity: which roads connect to this one
    private _connected = roadsConnectedTo _road;
    ArmaGM_roadGraph set [_road, _connected];

    // Road type info
    private _info = getRoadInfo _road;
    ArmaGM_roadInfo set [_road, _info select 0];

    // Position cache for fast lookups
    ArmaGM_roadPositions set [_road, getPos _road];
} forEach _allRoads;

private _elapsed = (diag_tickTime - _startTime) toFixed 2;
["ArmaGM graphGenRoads: Complete. %1 roads indexed in %2s", count _allRoads, _elapsed] call BIS_fnc_logFormat;
