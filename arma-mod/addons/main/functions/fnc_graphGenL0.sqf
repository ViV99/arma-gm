/*
  fnc_graphGenL0.sqf
  Strategic graph generator (Level 0).
  Finds named locations on the map, enriches with tactical data,
  builds road-based edges via BFS, sends JSON to GM server.
  Populates ArmaGM_nodePositions.
  Blocking call, runs on server only.
*/

if (!isServer) exitWith {};

private _startTime = diag_tickTime;
["ArmaGM graphGenL0: Generating strategic graph for %1", worldName] call BIS_fnc_logFormat;

// --- Helper: sanitize location name to valid ID ---
private _fnc_sanitizeName = {
    params ["_name"];
    private _lower = toLower _name;
    private _chars = toArray _lower;
    private _result = [];
    {
        // a-z = 97-122, 0-9 = 48-57, space = 32, dash = 45, underscore = 95
        if (_x >= 97 && _x <= 122) then {
            _result pushBack _x;
        } else {
            if (_x >= 48 && _x <= 57) then {
                _result pushBack _x;
            } else {
                if (_x == 32 || _x == 45) then {
                    _result pushBack 95; // underscore
                } else {
                    if (_x == 95) then {
                        _result pushBack 95;
                    };
                };
            };
        };
    } forEach _chars;
    toString _result
};

// --- 1. Get named locations ---
private _mapCenter = [worldSize / 2, worldSize / 2, 0];
private _locations = nearestLocations [_mapCenter,
    ["NameCity", "NameCityCapital", "NameVillage", "NameLocal", "Airport", "NameMarine"],
    worldSize
];

["ArmaGM graphGenL0: Found %1 raw locations", count _locations] call BIS_fnc_logFormat;

// --- 2. Build nodes, filtering weak NameLocal ---
private _nodes = [];       // [[id, name, pos, elevation, buildingCount, coverQuality, vehicleAccess, locType], ...]
private _nodeIds = [];     // For duplicate checking
private _nodeJsonList = [];

{
    private _loc = _x;
    private _locType = type _loc;
    private _pos = locationPosition _loc;
    private _name = text _loc;

    // Filter: NameLocal with few buildings = insignificant
    if (_locType == "NameLocal") then {
        private _nearBldg = nearestTerrainObjects [_pos, ["HOUSE", "BUILDING"], 200];
        if (count _nearBldg < 10) then { continue };
    };

    private _id = [_name] call _fnc_sanitizeName;

    // Skip duplicates (same sanitized name)
    if (_id in _nodeIds) then { continue };
    _nodeIds pushBack _id;

    // Enrich node data
    private _elevation = getTerrainHeightASL _pos;
    private _nearBuildings = nearestTerrainObjects [_pos, ["HOUSE", "BUILDING"], 200];
    private _buildingCount = count _nearBuildings;
    private _coverQuality = (_buildingCount / 50) min 1.0;
    private _nearRoads = nearestTerrainObjects [_pos, ["ROAD", "MAIN ROAD"], 100];
    private _vehicleAccess = count _nearRoads > 0;

    _nodes pushBack [_id, _name, _pos, _elevation, _buildingCount, _coverQuality, _vehicleAccess, _locType];
} forEach _locations;

["ArmaGM graphGenL0: %1 nodes after filtering", count _nodes] call BIS_fnc_logFormat;

// --- 3. Compute dominance for each node ---
{
    _x params ["_id", "_name", "_pos", "_elevation", "_buildingCount", "_coverQuality", "_vehicleAccess", "_locType"];
    private _neighborsInRange = 0;
    private _lowerNeighbors = 0;
    {
        if (_x select 0 == _id) then { continue };
        private _otherPos = _x select 2;
        private _otherElev = _x select 3;
        if (_pos distance2D _otherPos < 3000) then {
            _neighborsInRange = _neighborsInRange + 1;
            if (_otherElev < _elevation) then {
                _lowerNeighbors = _lowerNeighbors + 1;
            };
        };
    } forEach _nodes;

    private _dominance = if (_neighborsInRange > 0) then {
        _lowerNeighbors / _neighborsInRange
    } else { 0 };

    // Build node JSON
    private _vehicleStr = if (_vehicleAccess) then { "true" } else { "false" };
    _nodeJsonList pushBack format [
        "{""id"":""%1"",""name"":""%2"",""level"":0,""position"":[%3,%4,%5],""elevation"":%5,""properties"":{""cover_quality"":%6,""building_count"":%7,""vehicle_access"":%8,""dominance"":%9,""location_type"":""%10""}}",
        _id, _name,
        (_pos select 0) toFixed 2, (_pos select 1) toFixed 2, _elevation toFixed 2,
        _coverQuality toFixed 2, str _buildingCount, _vehicleStr, _dominance toFixed 2, _locType
    ];
} forEach _nodes;

// --- 4. Build edges via BFS on road network ---
private _edgeJsonList = [];

// Helper: find nearest road to a position
private _fnc_nearestRoad = {
    params ["_pos"];
    private _nearRoads = nearestTerrainObjects [_pos, ["ROAD", "MAIN ROAD", "TRACK"], 500];
    if (count _nearRoads > 0) then { _nearRoads select 0 } else { objNull };
};

// Helper: BFS on road graph from roadA to roadB
private _fnc_roadBFS = {
    params ["_startRoad", "_endRoad", "_maxDist"];
    private _endPos = ArmaGM_roadPositions getOrDefault [_endRoad, getPos _endRoad];
    private _visited = createHashMap;
    private _queue = [[_startRoad, 0]]; // [road, accumulated distance]
    private _found = false;
    private _totalDist = 0;
    private _roadTypes = createHashMap; // type → count

    _visited set [_startRoad, true];

    while { count _queue > 0 && !_found } do {
        // Pop front
        private _current = _queue deleteAt 0;
        _current params ["_curRoad", "_curDist"];

        if (_curRoad isEqualTo _endRoad) exitWith {
            _found = true;
            _totalDist = _curDist;
        };

        // Don't explore beyond max distance
        if (_curDist > _maxDist) then { continue };

        private _neighbors = ArmaGM_roadGraph getOrDefault [_curRoad, []];
        {
            if !(_visited getOrDefault [_x, false]) then {
                _visited set [_x, true];
                private _nPos = ArmaGM_roadPositions getOrDefault [_x, getPos _x];
                private _curPos = ArmaGM_roadPositions getOrDefault [_curRoad, getPos _curRoad];
                private _segDist = _curPos distance2D _nPos;
                private _newDist = _curDist + _segDist;

                // Track road type
                private _rType = ArmaGM_roadInfo getOrDefault [_x, "ROAD"];
                private _typeCount = _roadTypes getOrDefault [_rType, 0];
                _roadTypes set [_rType, _typeCount + 1];

                _queue pushBack [_x, _newDist];
            };
        } forEach _neighbors;
    };

    // Determine dominant road type
    private _dominantType = "ROAD";
    private _maxCount = 0;
    {
        if (_y > _maxCount) then {
            _maxCount = _y;
            _dominantType = _x;
        };
    } forEach _roadTypes;

    [_found, _totalDist, _dominantType]
};

// Helper: compute bearing between two positions
private _fnc_bearing = {
    params ["_from", "_to"];
    private _dx = (_to select 0) - (_from select 0);
    private _dy = (_to select 1) - (_from select 1);
    private _angle = _dx atan2 _dy;
    if (_angle < 0) then { _angle = _angle + 360 };
    _angle
};

// Helper: sample cover rating along a line
private _fnc_sampleCover = {
    params ["_fromPos", "_toPos"];
    private _samples = 5;
    private _coverHits = 0;
    for "_s" from 0 to (_samples - 1) do {
        private _t = (_s + 0.5) / _samples;
        private _samplePos = [
            (_fromPos select 0) + ((_toPos select 0) - (_fromPos select 0)) * _t,
            (_fromPos select 1) + ((_toPos select 1) - (_fromPos select 1)) * _t,
            0
        ];
        private _nearCover = nearestTerrainObjects [_samplePos, ["HOUSE", "BUILDING", "TREE", "BUSH"], 30];
        if (count _nearCover > 2) then { _coverHits = _coverHits + 1 };
    };
    _coverHits / _samples
};

// Build edges for each node pair
for "_i" from 0 to (count _nodes - 2) do {
    private _nodeA = _nodes select _i;
    _nodeA params ["_idA", "_nameA", "_posA", "_elevA"];

    for "_j" from (_i + 1) to (count _nodes - 1) do {
        private _nodeB = _nodes select _j;
        _nodeB params ["_idB", "_nameB", "_posB", "_elevB"];

        private _straightDist = _posA distance2D _posB;
        if (_straightDist > 5000) then { continue };

        // Find nearest roads to each node
        private _roadA = [_posA] call _fnc_nearestRoad;
        private _roadB = [_posB] call _fnc_nearestRoad;

        private _edgeDist = _straightDist;
        private _roadType = "none";
        private _vehicleTraversable = false;

        // Try road BFS if both nodes have nearby roads
        if (!isNull _roadA && !isNull _roadB) then {
            private _bfsResult = [_roadA, _roadB, _straightDist * 2] call _fnc_roadBFS;
            _bfsResult params ["_found", "_bfsDist", "_domType"];
            if (_found) then {
                _edgeDist = _bfsDist;
                _roadType = _domType;
                _vehicleTraversable = true;
            };
        };

        // Skip if no road path and too far for off-road
        if (_roadType == "none" && _straightDist > 2000) then { continue };

        private _bearing = [_posA, _posB] call _fnc_bearing;
        private _elevChange = _elevB - _elevA;
        private _coverRating = [_posA, _posB] call _fnc_sampleCover;
        private _vehStr = if (_vehicleTraversable) then { "true" } else { "false" };

        _edgeJsonList pushBack format [
            "{""from_node"":""%1"",""to_node"":""%2"",""distance"":%3,""bearing"":%4,""road_type"":""%5"",""elevation_change"":%6,""cover_rating"":%7,""vehicle_traversable"":%8}",
            _idA, _idB,
            _edgeDist toFixed 2, _bearing toFixed 2, _roadType,
            _elevChange toFixed 2, _coverRating toFixed 2, _vehStr
        ];
    };
};

["ArmaGM graphGenL0: %1 nodes, %2 edges", count _nodeJsonList, count _edgeJsonList] call BIS_fnc_logFormat;

// --- 5. Assemble full JSON ---
private _json = format [
    "{""map"":""%1"",""level"":0,""parent_node"":null,""nodes"":[%2],""edges"":[%3]}",
    worldName,
    _nodeJsonList joinString ",",
    _edgeJsonList joinString ","
];

// --- 6. Send to GM server ---
ArmaGM_graphResult = "";
"ArmaGM" callExtension ["send_graph", [_json]];

// Wait for response (up to 30s — large payload)
private _sendTimeout = diag_tickTime + 30;
waitUntil { sleep 0.2; ArmaGM_graphResult != "" || diag_tickTime > _sendTimeout };

if (ArmaGM_graphResult == "") then {
    ["ArmaGM graphGenL0: WARNING - No response from server after sending graph"] call BIS_fnc_logFormat;
};

// --- 7. Populate ArmaGM_nodePositions from generated nodes ---
{
    _x params ["_id", "_name", "_pos"];
    ArmaGM_nodePositions pushBack [_id, [_pos select 0, _pos select 1]];
} forEach _nodes;

private _elapsed = (diag_tickTime - _startTime) toFixed 2;
["ArmaGM graphGenL0: Complete. %1 nodes registered in %2s", count _nodes, _elapsed] call BIS_fnc_logFormat;
