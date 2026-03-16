/*
  fnc_sendState.sqf
  Send game state JSON to GM server via extension.
  params: ["_json", [], [""]]
*/

params ["_json"];

if (!isServer) exitWith {};

// Send via extension (returns immediately, response via ExtensionCallback)
"ArmaGM" callExtension ["send_state", [_json]];
