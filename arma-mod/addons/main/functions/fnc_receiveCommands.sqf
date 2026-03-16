/*
  fnc_receiveCommands.sqf
  Handle ExtensionCallback from ArmaGM extension.
  params: ["_function", "_data"]
*/

params ["_function", "_data"];

switch (_function) do {
    case "commands": {
        // Complete response received
        [_data] call ArmaGM_fnc_processCommands;
    };

    case "chunk_begin": {
        // Start of chunked response
        ArmaGM_chunkBuffer = [];
        ArmaGM_chunkTotal = parseNumber _data;
    };

    case "chunk_data": {
        // Received a data chunk
        ArmaGM_chunkBuffer pushBack _data;
    };

    case "chunk_end": {
        // All chunks received, assemble and process
        private _assembled = ArmaGM_chunkBuffer joinString "";
        ArmaGM_chunkBuffer = [];
        [_assembled] call ArmaGM_fnc_processCommands;
    };

    case "pong": {
        ["ArmaGM ping response: %1", _data] call BIS_fnc_logFormat;
    };

    case "error": {
        ["ArmaGM error from extension: %1", _data] call BIS_fnc_logFormat;
    };
};

// Internal function to process parsed commands JSON
ArmaGM_fnc_processCommands = {
    params ["_json"];

    // Parse JSON using Arma's parseJson (Arma 3 2.14+)
    private _parsed = parseJson _json;
    if (isNil "_parsed") exitWith {
        ["ArmaGM: Failed to parse commands JSON: %1", _json] call BIS_fnc_logFormat;
    };

    private _commands = _parsed getOrDefault ["commands", []];
    ["ArmaGM: Executing %1 commands", count _commands] call BIS_fnc_logFormat;

    {
        [_x] call ArmaGM_fnc_executeCommand;
    } forEach _commands;
};
