/*
  fnc_collectState.sqf
  Collect current game state and send to GM server.
*/

if (!isServer) exitWith {};

// --- Build friendly_forces array ---
private _forcesJson = [];
{
    params ["_grpId", "_grp"];
    if (isNull _grp) then { continue };

    private _aliveUnits = units _grp select { alive _x };
    if (count _aliveUnits == 0) then { continue };

    // Position: use leader or first alive unit
    private _ref = if (!isNull leader _grp && alive leader _grp) then { leader _grp } else { _aliveUnits select 0 };
    private _node = [getPosATL _ref] call ArmaGM_fnc_nearestNode;

    // Status
    private _status = _grp getVariable ["ArmaGM_status", "idle"];

    // Health aggregate
    private _health = 0;
    { _health = _health + (1 - (damage _x)) } forEach _aliveUnits;
    _health = _health / (count _aliveUnits);

    // Type
    private _type = _grp getVariable ["ArmaGM_type", "infantry_squad"];

    // Task
    private _task = _grp getVariable ["ArmaGM_task", ""];

    _forcesJson pushBack format [
        "{""id"":""%1"",""type"":""%2"",""size"":%3,""position"":""%4"",""status"":""%5"",""health"":%6,""ammo"":1.0,""current_task"":""%7""}",
        _grpId, _type, count _aliveUnits, _node, _status, _health toFixed 2, _task
    ];
} forEach ArmaGM_groups;

// --- Build enemy_contacts ---
private _contactsJson = [];

// Auto-detect: BLUFOR units known to OPFOR
private _knownEnemies = [];
{
    private _grp = _x select 1;
    {
        private _unit = _x;
        {
            if (alive _x && side _x == west && !(_x in _knownEnemies)) then {
                if (_unit knowsAbout _x > 0.5) then {
                    _knownEnemies pushBack _x;
                };
            };
        } forEach (allUnits select { side _x == west });
    } forEach (units _grp);
} forEach ArmaGM_groups;

// Group known enemies into contacts by proximity (~50m clusters)
private _contactGroups = [];
{
    private _pos = getPosATL _x;
    private _foundGroup = -1;
    {
        private _cg = _x;
        if ((_cg select 0) distance2D _pos < 50) exitWith { _foundGroup = _forEachIndex };
    } forEach _contactGroups;

    if (_foundGroup < 0) then {
        _contactGroups pushBack [_pos, [_x]];
    } else {
        (_contactGroups select _foundGroup select 1) pushBack _x;
    };
} forEach _knownEnemies;

{
    private _cg = _x;
    private _centerPos = _cg select 0;
    private _members = _cg select 1;
    private _contactId = format ["contact_%1", _forEachIndex];
    private _node = [_centerPos] call ArmaGM_fnc_nearestNode;
    private _size = count _members;
    private _estSize = if (_size >= 8) then {"squad"} else {if (_size >= 4) then {"fire_team"} else {"unknown"}};

    _contactsJson pushBack format [
        "{""id"":""%1"",""type"":""infantry"",""estimated_size"":""%2"",""position"":""%3"",""confidence"":0.7,""direction"":""unknown"",""last_seen"":%4}",
        _contactId, _estSize, _node, time toFixed 1
    ];
} forEach _contactGroups;

// Also add pre-defined contacts from ArmaGM_contacts
{
    params ["_id", "_type", "_estSize", "_node", "_confidence", "_direction", "_lastSeen"];
    _contactsJson pushBack format [
        "{""id"":""%1"",""type"":""%2"",""estimated_size"":""%3"",""position"":""%4"",""confidence"":%5,""direction"":""%6"",""last_seen"":%7}",
        _id, _type, _estSize, _node, _confidence toFixed 2, _direction, _lastSeen toFixed 1
    ];
} forEach ArmaGM_contacts;

// --- Build objectives ---
private _objJson = [];
{
    params ["_id", "_status", "_threat", "_node"];
    _objJson pushBack format [
        "{""id"":""%1"",""status"":""%2"",""threat_level"":""%3"",""graph_node"":""%4""}",
        _id, _status, _threat, _node
    ];
} forEach ArmaGM_objectives;

// --- Build events ---
private _eventsJson = [];
{
    params ["_evtType", "_evtData", "_evtTime"];
    _eventsJson pushBack format [
        "{""type"":""%1"",""data"":%2,""timestamp"":%3}",
        _evtType, _evtData, _evtTime toFixed 1
    ];
} forEach ArmaGM_events;
// Flush events buffer after collecting
ArmaGM_events = [];

// --- Resources ---
private _reserves = if (isNil "ArmaGM_reserves") then { [2, 1, true, false] } else { ArmaGM_reserves };
private _resJson = format [
    "{""reserve_infantry"":%1,""reserve_motorized"":%2,""artillery_available"":%3,""cas_available"":%4}",
    _reserves select 0,
    _reserves select 1,
    if (_reserves select 2) then {"true"} else {"false"},
    if (_reserves select 3) then {"true"} else {"false"}
];

// --- L2 local graph (if requested via request_intel) ---
private _localJson = "null";
if (!isNil "ArmaGM_intelNode" && { ArmaGM_intelNode != "" }) then {
    _localJson = [ArmaGM_intelNode, 150] call ArmaGM_fnc_graphExtract;
    // Cache expires after one tick
    ArmaGM_intelNode = "";
};

// --- Dynamic node updates ---
private _nodeUpdatesJson = "{}";
if (!isNil "ArmaGM_nodeUpdates" && { count ArmaGM_nodeUpdates > 0 }) then {
    private _pairs = [];
    {
        private _nId = _x;
        private _props = _y;
        private _propPairs = [];
        {
            private _valStr = switch (true) do {
                case (_y isEqualType true): { if (_y) then {"true"} else {"false"} };
                case (_y isEqualType 0): { _y toFixed 4 };
                default { format ['"%1"', _y] };
            };
            _propPairs pushBack format ['"%1":%2', _x, _valStr];
        } forEach _props;
        _pairs pushBack format ['"%1":{%2}', _nId, _propPairs joinString ","];
    } forEach ArmaGM_nodeUpdates;
    _nodeUpdatesJson = format ["{%1}", _pairs joinString ","];
};

// --- Assemble full JSON ---
private _json = format [
    "{""tick_id"":%1,""mission_time"":%2,""friendly_forces"":[%3],""enemy_contacts"":[%4],""objectives"":[%5],""events_since_last_tick"":[%6],""resources"":%7,""graph"":{""strategic"":{},""tactical"":{},""local"":%8,""node_updates"":%9},""pacing"":{""current_phase"":""calm"",""intensity"":0.0,""phase_ticks"":0}}",
    ArmaGM_tickId,
    time toFixed 1,
    _forcesJson joinString ",",
    _contactsJson joinString ",",
    _objJson joinString ",",
    _eventsJson joinString ",",
    _resJson,
    _localJson,
    _nodeUpdatesJson
];

// Send to GM server
[_json] call ArmaGM_fnc_sendState;
