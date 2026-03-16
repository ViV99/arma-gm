/*
  fnc_cmdDespawnGroup.sqf
  Execute despawn_group command: remove a group and all its units from the world.
  params: hashmap with keys: unit (str), reason (str, optional)
*/

params ["_p"];

private _unitId = _p getOrDefault ["unit", ""];
private _reason = _p getOrDefault ["reason", "despawned by GM"];

// Find group by id
private _grp = grpNull;
{
    params ["_id", "_g"];
    if (_id == _unitId) exitWith { _grp = _g };
} forEach ArmaGM_groups;

if (isNull _grp) exitWith {
    ["ArmaGM despawn_group: group '%1' not found", _unitId] call BIS_fnc_logFormat;
};

// Delete all units in the group
{ deleteVehicle _x } forEach units _grp;

// Delete the group itself
deleteGroup _grp;

// Remove from ArmaGM_groups registry
ArmaGM_groups = ArmaGM_groups select { (_x select 0) != _unitId };

["ArmaGM: Group '%1' despawned — reason: %2", _unitId, _reason] call BIS_fnc_logFormat;
