/*
  fnc_graphExtract.sqf
  Extract L2 local graph for a given node ID.
  Scans buildings and cover objects in a radius, clusters them into nodes,
  builds edges between them.

  params: ["_nodeId", "_radius"]
  returns: JSON string (game_state.graph.local format)

  Called when LLM issues request_intel, result included in next tick's state.
*/

params ["_nodeId", ["_radius", 150]];

private _centerPos = [_nodeId] call ArmaGM_fnc_getNodePos;
if (_centerPos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM graphExtract: node '%1' not found", _nodeId] call BIS_fnc_logFormat;
    "{}"
};

// --- Scan buildings ---
private _buildings = nearestObjects [_centerPos, ["Building"], _radius];

// Cluster buildings by proximity (30m threshold)
private _clusters = [];  // [[centerPos, [building, ...]], ...]
{
    private _bPos = getPosATL _x;
    private _placed = false;
    {
        private _clusterCenter = _x select 0;
        if (_clusterCenter distance2D _bPos < 30) exitWith {
            (_x select 1) pushBack _building;
            _placed = true;
        };
    } forEach _clusters;
    if (!_placed) then {
        _clusters pushBack [_bPos, [_x]];
    };
} forEach _buildings;

// Scan cover objects (walls, rocks, wrecks)
private _coverObjs = nearestObjects [_centerPos, ["Wall_F","Rock_Base_F","RoadBarrier_F","CarWreck"], _radius];

// --- Build L2 nodes ---
private _nodeJsonList = [];
private _edgeJsonList = [];
private _nodePositions = [];  // [[nodeId, pos], ...] for edge building

// Cluster-based building nodes
{
    private _cl = _x;
    private _clPos = _cl select 0;
    private _members = _cl select 1;
    private _idx = _forEachIndex;
    private _nId = format ["%1_bldg_%2", _nodeId, _idx];
    private _nName = format ["building cluster %1", _idx];

    // Count floors from tallest building in cluster
    private _maxFloors = 0;
    {
        private _floors = 0;
        while { !isNil { _x buildingPos _floors } && { !(_x buildingPos _floors isEqualTo [0,0,0]) } } do {
            _floors = _floors + 1;
            if (_floors > 10) exitWith {};  // safety
        };
        if (_floors > _maxFloors) then { _maxFloors = _floors };
    } forEach _members;

    private _coverQuality = if (_maxFloors > 1) then { 0.85 } else { 0.65 };

    _nodePositions pushBack [_nId, _clPos];
    _nodeJsonList pushBack format [
        "{""id"":""%1"",""name"":""%2"",""level"":2,""position"":[%3,%4,0],""elevation"":0,""properties"":{""floors"":%5,""cover_quality"":%6,""building_count"":%7,""tactical_suitability"":[""defense"",""overwatch""]}}",
        _nId, _nName,
        (_clPos select 0) toFixed 1, (_clPos select 1) toFixed 1,
        _maxFloors, _coverQuality toFixed 2, count _members
    ];
} forEach _clusters;

// Cover objects node (if significant)
if (count _coverObjs > 0) then {
    private _coverId = format ["%1_cover_0", _nodeId];
    // Approximate center of cover objects
    private _cx = 0; private _cy = 0;
    { private _p = getPosATL _x; _cx = _cx + (_p select 0); _cy = _cy + (_p select 1) } forEach _coverObjs;
    _cx = _cx / (count _coverObjs); _cy = _cy / (count _coverObjs);
    _nodePositions pushBack [_coverId, [_cx, _cy]];
    _nodeJsonList pushBack format [
        "{""id"":""%1"",""name"":""cover position"",""level"":2,""position"":[%2,%3,0],""elevation"":0,""properties"":{""cover_type"":""hard cover"",""cover_quality"":0.7,""tactical_suitability"":[""defense"",""ambush""]}}",
        _coverId, _cx toFixed 1, _cy toFixed 1
    ];
};

// --- Build edges between nodes (within 80m of each other) ---
private _n = count _nodePositions;
for "_i" from 0 to (_n - 2) do {
    private _a = _nodePositions select _i;
    private _aId = _a select 0;
    private _aPos = _a select 1;
    for "_j" from (_i + 1) to (_n - 1) do {
        private _b = _nodePositions select _j;
        private _bId = _b select 0;
        private _bPos = _b select 1;
        private _dist = _aPos distance2D _bPos;
        if (_dist <= 80) then {
            // Estimate cover on route (average of endpoints)
            _edgeJsonList pushBack format [
                "{""from_node"":""%1"",""to_node"":""%2"",""distance"":%3,""road_type"":""path"",""cover_rating"":0.3,""vehicle_traversable"":false}",
                _aId, _bId, _dist toFixed 1
            ];
        };
    };
};

// --- Assemble JSON ---
format [
    "{""level"":2,""center_node"":""%1"",""nodes"":[%2],""edges"":[%3]}",
    _nodeId,
    _nodeJsonList joinString ",",
    _edgeJsonList joinString ","
]
