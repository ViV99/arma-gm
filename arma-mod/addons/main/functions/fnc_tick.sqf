/*
  fnc_tick.sqf
  Main GM tick loop. Runs as a scheduled script on the server.
  Collects game state and sends to GM server every ArmaGM_tickInterval seconds.
*/

if (!isServer) exitWith {};

private _tickInterval = if (isNil "ArmaGM_tickInterval") then { 15 } else { ArmaGM_tickInterval };

while { true } do {
    sleep _tickInterval;

    // Collect state and send to GM server
    [] call ArmaGM_fnc_collectState;

    // Increment tick
    ArmaGM_tickId = ArmaGM_tickId + 1;
};
