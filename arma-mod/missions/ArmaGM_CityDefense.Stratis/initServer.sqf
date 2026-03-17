/*
  initServer.sqf - Server-side mission initialization.
  Runs only on the server/host.
*/

waitUntil { !isNull (findDisplay 46) || !hasInterface }; // Wait for game loaded

// Node positions populated automatically by graph generation
ArmaGM_nodePositions = [];

// Wait for graph generation to complete before setting up mission
waitUntil { sleep 1; ArmaGM_graphReady };

// Load and run setup scripts (synchronous execution)
call compile preprocessFileLineNumbers "scripts\setupDefenders.sqf";
[] call ArmaGM_setupDefenders;

call compile preprocessFileLineNumbers "scripts\setupObjectives.sqf";
[] call ArmaGM_setupObjectives;

// Start end-condition checker
execVM "scripts\endConditions.sqf";

// ArmaGM_fnc_init runs automatically via preInit in CfgFunctions
