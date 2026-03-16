/*
  init.sqf - Client-side initialization
  Runs on all machines (clients and server).
*/

// Set GM server URL (override before ArmaGM_fnc_init runs)
// Change this to the machine running gm-server if different from localhost
ArmaGM_serverUrl = "http://127.0.0.1:8080";
ArmaGM_tickInterval = 15; // seconds between GM ticks
