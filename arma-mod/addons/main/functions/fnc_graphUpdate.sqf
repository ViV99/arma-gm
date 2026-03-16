/*
  fnc_graphUpdate.sqf
  Apply a dynamic update to a graph node's properties.
  Updates are accumulated in ArmaGM_nodeUpdates and sent to GM server
  with every game state tick.

  params: ["_nodeId", "_property", "_value"]

  Examples:
    ["agia_marina_warehouse", "cover_quality", 0.2] call ArmaGM_fnc_graphUpdate
    ["agia_marina_road_south", "vehicle_traversable", false] call ArmaGM_fnc_graphUpdate

  Called from:
    - EntityKilled EH (building destroyed -> cover drops)
    - Vehicle wreck events (road blocked)
    - Fortification built events (cover improves)
*/

params ["_nodeId", "_property", "_value"];

if (isNil "ArmaGM_nodeUpdates") then {
    ArmaGM_nodeUpdates = createHashMap;
};

// Get existing overrides for this node (or empty hashmap)
private _existing = ArmaGM_nodeUpdates getOrDefault [_nodeId, createHashMap];
_existing set [_property, _value];
ArmaGM_nodeUpdates set [_nodeId, _existing];

["ArmaGM graphUpdate: %1.%2 = %3", _nodeId, _property, _value] call BIS_fnc_logFormat;
