/*
  fnc_nearestNode.sqf
  Find the nearest graph node to a given position.
  params: ["_pos", [], [[]]]
  returns: string node ID, or "unknown" if not found
*/

params ["_pos"];

if (isNil "ArmaGM_nodePositions") exitWith { "unknown" };
if (count ArmaGM_nodePositions == 0) exitWith { "unknown" };

private _bestId = "unknown";
private _bestDist = 1e10;

{
    params ["_id", "_nodePos"];
    // _nodePos is [x, y] 2D position
    private _dx = (_pos select 0) - (_nodePos select 0);
    private _dy = (_pos select 1) - (_nodePos select 1);
    private _dist = sqrt (_dx * _dx + _dy * _dy);
    if (_dist < _bestDist) then {
        _bestDist = _dist;
        _bestId = _id;
    };
} forEach ArmaGM_nodePositions;

_bestId

// --- Companion function: get node position ---
ArmaGM_fnc_getNodePos = {
    params ["_nodeId"];
    private _result = [0, 0, 0];
    {
        params ["_id", "_pos"];
        if (_id == _nodeId) exitWith { _result = [_pos select 0, _pos select 1, 0] };
    } forEach ArmaGM_nodePositions;
    _result
};
