/*
  fnc_cmdCreateRoadblock.sqf
  Execute create_roadblock command: place barrier objects and optionally assign a unit to hold.
  params: hashmap with keys: location (str), unit (str, optional)
*/

params ["_p"];

private _location = _p getOrDefault ["location", ""];
private _unitId = _p getOrDefault ["unit", ""];

// Get node position
private _nodePos = [_location] call ArmaGM_fnc_getNodePos;
if (_nodePos isEqualTo [0,0,0]) exitWith {
    ["ArmaGM create_roadblock: node '%1' not found", _location] call BIS_fnc_logFormat;
};

// Place 3 barrier objects around the node
private _barrierType = "Land_BagFence_Long_F";
createVehicle [_barrierType, _nodePos getPos [4, 0],   [], 0, "CAN_COLLIDE"];
createVehicle [_barrierType, _nodePos getPos [4, 120],  [], 0, "CAN_COLLIDE"];
createVehicle [_barrierType, _nodePos getPos [4, 240],  [], 0, "CAN_COLLIDE"];

// Optionally assign a unit group to hold the roadblock
if (_unitId != "") then {
    private _grp = grpNull;
    {
        params ["_id", "_g"];
        if (_id == _unitId) exitWith { _grp = _g };
    } forEach ArmaGM_groups;

    if (!isNull _grp) then {
        while { (count waypoints _grp) > 0 } do {
            deleteWaypoint [_grp, 0];
        };
        private _wp = _grp addWaypoint [_nodePos, 0];
        _wp setWaypointType "HOLD";
        _wp setWaypointSpeed "NORMAL";
        _wp setWaypointBehaviour "AWARE";
        _wp setWaypointCombatMode "YELLOW";
        _wp setWaypointCompletionRadius 15;

        _grp setVariable ["ArmaGM_status", "roadblock"];
        _grp setVariable ["ArmaGM_task", format ["holding roadblock at %1", _location]];
    } else {
        ["ArmaGM create_roadblock: unit '%1' not found, barriers placed without guard", _unitId] call BIS_fnc_logFormat;
    };
};

["ArmaGM: Roadblock established at %1", _location] call BIS_fnc_logFormat;
