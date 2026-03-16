/*
  fnc_eventContact.sqf
  Handle new enemy contact detection.
  Called manually or from AI detection logic.
  params: ["_unit", "_contactPos", "_contactType"]
*/

params ["_unit", "_contactPos", "_contactType"];

private _node = [_contactPos] call ArmaGM_fnc_nearestNode;
private _contactId = format ["contact_%1", (floor random 9000) + 1000];

// Add to events buffer
ArmaGM_events pushBack [
    "contact_new",
    format ['{"contact_id":"%1","location":"%2"}', _contactId, _node],
    time
];

["ArmaGM: New contact %1 at %2 (%3)", _contactId, _node, _contactType] call BIS_fnc_logFormat;
