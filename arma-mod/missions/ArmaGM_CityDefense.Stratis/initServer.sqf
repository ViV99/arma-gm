/*
  initServer.sqf - Server-side mission initialization.
  Runs only on the server/host.
*/

waitUntil { !isNull (findDisplay 46) || !hasInterface }; // Wait for game loaded

// Set up graph node positions for Agia Marina
// These correspond to nodes in shared/maps/stratis/tactical/agia_marina.json
ArmaGM_nodePositions = [
    ["agia_marina_crossroad",   [2300, 2600]],
    ["agia_marina_church",      [2320, 2620]],
    ["agia_marina_east",        [2400, 2620]],
    ["agia_marina_west",        [2200, 2610]],
    ["agia_marina_north",       [2300, 2680]],
    ["agia_marina_south",       [2300, 2520]],
    ["agia_marina_market",      [2315, 2605]],
    ["agia_marina_dock",        [2260, 2590]],
    ["agia_marina_hill_east",   [2440, 2650]],
    ["agia_marina_hill_west",   [2170, 2640]],
    ["agia_marina_school",      [2330, 2640]],
    ["agia_marina_gas_station", [2285, 2595]],
    ["agia_marina_warehouse",   [2220, 2650]],
    ["agia_marina_parking",     [2350, 2590]],
    ["agia_marina_road_north",  [2300, 2720]],
    ["agia_marina_road_south",  [2300, 2480]],
    ["agia_marina_road_west",   [2160, 2590]],
    ["agia_marina_alley_1",     [2340, 2610]],
    ["agia_marina_alley_2",     [2270, 2610]],
    ["agia_marina_rooftop_north", [2310, 2660]],
    ["agia_marina_rooftop_south", [2305, 2560]],
    ["agia_marina_garden",      [2295, 2635]],
    ["agia_marina_wall_east",   [2390, 2600]],
    ["agia_marina_bridge",      [2270, 2540]],
    ["agia_marina_tower",       [2360, 2660]]
];

// Load and run setup scripts (synchronous execution)
call compile preprocessFileLineNumbers "scripts\setupDefenders.sqf";
[] call ArmaGM_setupDefenders;

call compile preprocessFileLineNumbers "scripts\setupObjectives.sqf";
[] call ArmaGM_setupObjectives;

// Start end-condition checker
execVM "scripts\endConditions.sqf";

// ArmaGM_fnc_init runs automatically via preInit in CfgFunctions
