/*
  fnc_cmdSetPatrol.sqf
  Execute set_patrol command: assign a cyclic patrol route through a list of nodes.
  params: hashmap with keys: unit (str), route_nodes (array of strings)
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _routeNodes = _p getOrDefault ["route_nodes", []];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM set_patrol: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

if ((count _routeNodes) == 0) exitWith {
    ["ArmaGM set_patrol: no route_nodes specified for '%1'", _unitId] call BIS_fnc_logFormat;
};

// Clear existing waypoints
while { (count waypoints _grp) > 0 } do {
    deleteWaypoint [_grp, 0];
};

// Add a MOVE waypoint for each node in the route
private _firstPos = [0,0,0];
private _nodeCount = count _routeNodes;
{
    private _nodeId = _x;
    private _nodePos = [_nodeId] call ArmaGM_fnc_getNodePos;
    if !(_nodePos isEqualTo [0,0,0]) then {
        if (_firstPos isEqualTo [0,0,0]) then { _firstPos = _nodePos };
        private _wp = _grp addWaypoint [_nodePos, 0];
        _wp setWaypointType "MOVE";
        _wp setWaypointSpeed "NORMAL";
        _wp setWaypointBehaviour "AWARE";
        _wp setWaypointCombatMode "YELLOW";
        _wp setWaypointCompletionRadius 20;
    };
} forEach _routeNodes;

// Add CYCLE waypoint at first node position to loop the patrol
if !(_firstPos isEqualTo [0,0,0]) then {
    private _cycleWp = _grp addWaypoint [_firstPos, 0];
    _cycleWp setWaypointType "CYCLE";
};

_grp setVariable ["ArmaGM_status", "patrolling"];
_grp setVariable ["ArmaGM_task", format ["patrolling %1 nodes", _nodeCount]];

["ArmaGM: %1 patrolling %2 nodes", _unitId, _nodeCount] call BIS_fnc_logFormat;
