/*
  fnc_graphGenL1.sqf
  Tactical graph generator (Level 1) for a single zone.
  Clusters buildings into block nodes, detects intersections, approaches,
  open areas, hills, and special buildings.
  Runs in background via spawn.

  params: ["_parentId", "_centerPos", "_radius"]
*/

params ["_parentId", "_centerPos", "_radius"];

if (!isServer) exitWith {};

private _startTime = diag_tickTime;
["ArmaGM graphGenL1: Generating tactical graph for %1 (r=%2m)", _parentId, _radius] call BIS_fnc_logFormat;

// --- 1. Scan buildings ---
private _buildings = nearestTerrainObjects [_centerPos,
    ["HOUSE", "BUILDING", "CHURCH", "BUNKER", "CHAPEL", "FUELSTATION", "HOSPITAL"],
    _radius
];

// --- 2. Cluster buildings by 50m proximity ---
private _clusters = []; // [[centerPos, [building, ...]], ...]
{
    private _bPos = getPosATL _x;
    private _placed = false;
    {
        private _clusterCenter = _x select 0;
        if (_clusterCenter distance2D _bPos < 50) exitWith {
            (_x select 1) pushBack _x;
            // Recalculate center as average
            private _members = _x select 1;
            private _cx = 0; private _cy = 0;
            { private _p = getPosATL _x; _cx = _cx + (_p select 0); _cy = _cy + (_p select 1) } forEach _members;
            _x set [0, [_cx / count _members, _cy / count _members, 0]];
            _placed = true;
        };
    } forEach _clusters;
    if (!_placed) then {
        _clusters pushBack [_bPos, [_x]];
    };
} forEach _buildings;

// --- Collect all nodes ---
// Each: [id, name, type, pos, properties_json]
private _allNodes = [];
private _nodePositions = []; // [[id, pos], ...] for edge building

// Sort clusters by position (X asc, Y asc) for stable IDs
_clusters sort true; // sorts by first element (position array)

// Block nodes from building clusters
private _blockIdx = 0;
{
    _x params ["_clPos", "_members"];
    private _id = format ["%1_block_%2", _parentId, _blockIdx];
    private _name = format ["block %1", _blockIdx];
    private _elevation = getTerrainHeightASL _clPos;
    private _buildingCount = count _members;
    private _coverQuality = ((_buildingCount / 20) min 1.0) max 0.3;
    private _nearRoads = nearestTerrainObjects [_clPos, ["ROAD", "MAIN ROAD"], 50];
    private _vehicleAccess = count _nearRoads > 0;
    private _vehicleStr = if (_vehicleAccess) then { "true" } else { "false" };

    _allNodes pushBack [_id, _name, "block", _clPos, format [
        """cover_quality"":%1,""building_count"":%2,""vehicle_access"":%3",
        _coverQuality toFixed 2, str _buildingCount, _vehicleStr
    ]];
    _nodePositions pushBack [_id, _clPos];
    _blockIdx = _blockIdx + 1;
} forEach _clusters;

// --- 3. Road intersections (>2 connections) ---
private _zoneRoads = nearestTerrainObjects [_centerPos, ["ROAD", "MAIN ROAD", "TRACK"], _radius];
private _crossIdx = 0;
{
    private _road = _x;
    private _connected = roadsConnectedTo _road;
    if (count _connected > 2) then {
        private _rPos = getPos _road;
        // Skip if too close to an existing node (< 30m)
        private _tooClose = false;
        { if ((_x select 1) distance2D _rPos < 30) exitWith { _tooClose = true } } forEach _nodePositions;
        if (!_tooClose) then {
            private _id = format ["%1_cross_%2", _parentId, _crossIdx];
            private _elevation = getTerrainHeightASL _rPos;
            _allNodes pushBack [_id, format ["intersection %1", _crossIdx], "cross", _rPos, format [
                """cover_quality"":0.1,""vehicle_access"":true",
            ""]];
            _nodePositions pushBack [_id, _rPos];
            _crossIdx = _crossIdx + 1;
        };
    };
} forEach _zoneRoads;

// --- 4. Approach nodes (roads crossing zone boundary) ---
private _approachIdx = 0;
{
    private _road = _x;
    private _rPos = getPos _road;
    // Only roads near the boundary
    private _distFromCenter = _centerPos distance2D _rPos;
    if (_distFromCenter > _radius * 0.8 && _distFromCenter <= _radius) then {
        private _connected = roadsConnectedTo _road;
        private _hasOutside = false;
        { if (_centerPos distance2D (getPos _x) > _radius) exitWith { _hasOutside = true } } forEach _connected;
        if (_hasOutside) then {
            // Skip if too close to existing node
            private _tooClose = false;
            { if ((_x select 1) distance2D _rPos < 40) exitWith { _tooClose = true } } forEach _nodePositions;
            if (!_tooClose) then {
                private _id = format ["%1_approach_%2", _parentId, _approachIdx];
                private _elevation = getTerrainHeightASL _rPos;
                _allNodes pushBack [_id, format ["approach %1", _approachIdx], "approach", _rPos, format [
                    """cover_quality"":0.15,""vehicle_access"":true",
                ""]];
                _nodePositions pushBack [_id, _rPos];
                _approachIdx = _approachIdx + 1;
            };
        };
    };
} forEach _zoneRoads;

// --- 5. Open areas (gaps > 60m between clusters) ---
private _openIdx = 0;
if (count _clusters > 1) then {
    for "_i" from 0 to (count _clusters - 2) do {
        private _cA = (_clusters select _i) select 0;
        for "_j" from (_i + 1) to (count _clusters - 1) do {
            private _cB = (_clusters select _j) select 0;
            if (_cA distance2D _cB > 120) then {
                // Midpoint between distant clusters
                private _midPos = [
                    ((_cA select 0) + (_cB select 0)) / 2,
                    ((_cA select 1) + (_cB select 1)) / 2,
                    0
                ];
                // Only if within zone and no buildings nearby
                if (_centerPos distance2D _midPos < _radius) then {
                    private _nearBldg = nearestTerrainObjects [_midPos, ["HOUSE", "BUILDING"], 30];
                    if (count _nearBldg == 0) then {
                        // Skip if too close to existing node
                        private _tooClose = false;
                        { if ((_x select 1) distance2D _midPos < 40) exitWith { _tooClose = true } } forEach _nodePositions;
                        if (!_tooClose) then {
                            private _id = format ["%1_open_%2", _parentId, _openIdx];
                            _allNodes pushBack [_id, format ["open area %1", _openIdx], "open", _midPos, format [
                                """cover_quality"":0.05,""vehicle_access"":true",
                            ""]];
                            _nodePositions pushBack [_id, _midPos];
                            _openIdx = _openIdx + 1;
                        };
                    };
                };
            };
        };
    };
};

// --- 6. Hill nodes (significantly higher terrain) ---
// Compute zone average elevation
private _totalElev = 0;
private _sampleCount = 0;
{
    _totalElev = _totalElev + getTerrainHeightASL (_x select 1);
    _sampleCount = _sampleCount + 1;
} forEach _nodePositions;
private _avgElev = if (_sampleCount > 0) then { _totalElev / _sampleCount } else { getTerrainHeightASL _centerPos };

private _hillIdx = 0;
// Sample grid around center for high points
private _step = _radius / 3;
for "_gx" from (-_radius) to _radius step _step do {
    for "_gy" from (-_radius) to _radius step _step do {
        private _samplePos = [(_centerPos select 0) + _gx, (_centerPos select 1) + _gy, 0];
        if (_centerPos distance2D _samplePos <= _radius) then {
            private _elev = getTerrainHeightASL _samplePos;
            if (_elev - _avgElev > 10) then {
                // Skip if too close to existing node
                private _tooClose = false;
                { if ((_x select 1) distance2D _samplePos < 50) exitWith { _tooClose = true } } forEach _nodePositions;
                if (!_tooClose) then {
                    private _id = format ["%1_hill_%2", _parentId, _hillIdx];
                    _allNodes pushBack [_id, format ["hill %1", _hillIdx], "hill", _samplePos, format [
                        """cover_quality"":0.2,""vehicle_access"":false,""dominance"":0.8",
                    ""]];
                    _nodePositions pushBack [_id, _samplePos];
                    _hillIdx = _hillIdx + 1;
                };
            };
        };
    };
};

// --- 7. Special buildings (churches, hospitals) ---
private _specialTypes = [["CHURCH", "church"], ["HOSPITAL", "hospital"], ["BUNKER", "bunker"], ["CHAPEL", "chapel"]];
{
    _x params ["_sqfType", "_label"];
    private _specials = nearestTerrainObjects [_centerPos, [_sqfType], _radius];
    private _specIdx = 0;
    {
        private _sPos = getPosATL _x;
        // Skip if too close to existing node
        private _tooClose = false;
        { if ((_x select 1) distance2D _sPos < 20) exitWith { _tooClose = true } } forEach _nodePositions;
        if (!_tooClose) then {
            private _id = format ["%1_%2_%3", _parentId, _label, _specIdx];
            private _elevation = getTerrainHeightASL _sPos;
            _allNodes pushBack [_id, format ["%1", _label], _label, _sPos, format [
                """cover_quality"":0.75,""building_count"":1,""vehicle_access"":false,""special"":true",
            ""]];
            _nodePositions pushBack [_id, _sPos];
            _specIdx = _specIdx + 1;
        };
    } forEach _specials;
} forEach _specialTypes;

// --- 8. Cap at 40 nodes: merge closest clusters if over ---
if (count _allNodes > 40) then {
    ["ArmaGM graphGenL1: %1 has %2 nodes, capping at 40", _parentId, count _allNodes] call BIS_fnc_logFormat;
    // Sort by priority: special > block > cross > approach > hill > open
    // Remove excess open/hill nodes first
    private _priorityOrder = ["church", "hospital", "bunker", "chapel", "block", "cross", "approach", "hill", "open"];
    _allNodes sort false; // reverse to process from end
    while { count _allNodes > 40 } do {
        // Remove last node (lowest priority after sort)
        private _removed = _allNodes deleteAt (count _allNodes - 1);
        private _removedId = _removed select 0;
        // Also remove from nodePositions
        private _npIdx = _nodePositions findIf { (_x select 0) == _removedId };
        if (_npIdx >= 0) then { _nodePositions deleteAt _npIdx };
    };
};

// --- 9. Build node JSON ---
private _nodeJsonList = [];
{
    _x params ["_id", "_name", "_type", "_pos", "_propsJson"];
    private _elevation = getTerrainHeightASL _pos;
    _nodeJsonList pushBack format [
        "{""id"":""%1"",""name"":""%2"",""level"":1,""position"":[%3,%4,%5],""elevation"":%5,""properties"":{%6,""node_type"":""%7""}}",
        _id, _name,
        (_pos select 0) toFixed 2, (_pos select 1) toFixed 2, _elevation toFixed 2,
        _propsJson, _type
    ];
} forEach _allNodes;

// --- 10. Build edges between nodes within 150m ---
private _edgeJsonList = [];
private _n = count _nodePositions;
for "_i" from 0 to (_n - 2) do {
    private _a = _nodePositions select _i;
    _a params ["_aId", "_aPos"];
    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _nodePositions select _j;
        _b params ["_bId", "_bPos"];
        private _dist = _aPos distance2D _bPos;
        if (_dist <= 150) then {
            // Check if road exists between them
            private _midPos = [
                ((_aPos select 0) + (_bPos select 0)) / 2,
                ((_aPos select 1) + (_bPos select 1)) / 2,
                0
            ];
            private _nearRoad = nearestTerrainObjects [_midPos, ["ROAD", "MAIN ROAD", "TRACK"], 25];
            private _roadType = if (count _nearRoad > 0) then {
                private _info = getRoadInfo (_nearRoad select 0);
                _info select 0
            } else { "path" };

            // Sample cover rating
            private _coverHits = 0;
            private _samples = 3;
            for "_s" from 0 to (_samples - 1) do {
                private _t = (_s + 0.5) / _samples;
                private _samplePos = [
                    (_aPos select 0) + ((_bPos select 0) - (_aPos select 0)) * _t,
                    (_aPos select 1) + ((_bPos select 1) - (_aPos select 1)) * _t,
                    0
                ];
                private _nearCover = nearestTerrainObjects [_samplePos, ["HOUSE", "BUILDING", "TREE", "WALL"], 20];
                if (count _nearCover > 1) then { _coverHits = _coverHits + 1 };
            };
            private _coverRating = _coverHits / _samples;

            private _vehStr = if (_roadType != "path") then { "true" } else { "false" };

            _edgeJsonList pushBack format [
                "{""from_node"":""%1"",""to_node"":""%2"",""distance"":%3,""road_type"":""%4"",""cover_rating"":%5,""vehicle_traversable"":%6}",
                _aId, _bId,
                _dist toFixed 2, _roadType, _coverRating toFixed 2, _vehStr
            ];
        };
    };
};

["ArmaGM graphGenL1: %1 — %2 nodes, %3 edges", _parentId, count _nodeJsonList, count _edgeJsonList] call BIS_fnc_logFormat;

// --- 11. Assemble JSON ---
private _json = format [
    "{""map"":""%1"",""level"":1,""parent_node"":""%2"",""nodes"":[%3],""edges"":[%4]}",
    worldName, _parentId,
    _nodeJsonList joinString ",",
    _edgeJsonList joinString ","
];

// --- 12. Send to GM server ---
ArmaGM_graphResult = "";
"ArmaGM" callExtension ["send_graph", [_json]];

// Wait for response (up to 20s)
private _sendTimeout = diag_tickTime + 20;
waitUntil { sleep 0.2; ArmaGM_graphResult != "" || diag_tickTime > _sendTimeout };

if (ArmaGM_graphResult == "") then {
    ["ArmaGM graphGenL1: WARNING - No response from server for %1", _parentId] call BIS_fnc_logFormat;
} else {
    // Parse response and append to ArmaGM_nodePositions
    private _parsed = parseJson ArmaGM_graphResult;
    if (!isNil "_parsed") then {
        private _respNodes = _parsed getOrDefault ["nodes", []];
        {
            private _nId = _x getOrDefault ["id", ""];
            private _nPos = _x getOrDefault ["position", [0, 0, 0]];
            if (_nId != "") then {
                ArmaGM_nodePositions pushBack [_nId, [_nPos select 0, _nPos select 1]];
            };
        } forEach _respNodes;
    };
};

private _elapsed = (diag_tickTime - _startTime) toFixed 2;
["ArmaGM graphGenL1: %1 complete in %2s", _parentId, _elapsed] call BIS_fnc_logFormat;
