class CfgPatches {
    class ArmaGM_Main {
        name = "ArmaGM Main";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.58;
        requiredAddons[] = {};
        authors[] = {"ArmaGM Project"};
        url = "";
        version = "0.1";
    };
};

class CfgFunctions {
    class ArmaGM {
        tag = "ArmaGM";
        class Main {
            file = "\ArmaGM\addons\main\functions";
            class fnc_init        { preInit = 1; };
            class fnc_tick        {};
            class fnc_collectState {};
            class fnc_sendState   {};
            class fnc_receiveCommands {};
            class fnc_executeCommand {};
            class fnc_cmdMoveSquad {};
            class fnc_cmdPositionSquad {};
            class fnc_cmdSetBehaviour {};
            class fnc_cmdReinforce {};
            class fnc_cmdRetreat {};
            class fnc_eventKilled {};
            class fnc_eventContact {};
            class fnc_nearestNode {};
            class fnc_graphExtract {};
            class fnc_graphUpdate {};
            class fnc_graphGenInit {};
            class fnc_graphGenRoads {};
            class fnc_graphGenL0 {};
            class fnc_graphGenL1 {};
            class fnc_cmdArtilleryStrike {};
            class fnc_cmdSetAmbush {};
            class fnc_cmdSetFortify {};
            class fnc_cmdSetPatrol {};
            class fnc_cmdSetOverwatch {};
            class fnc_cmdSpawnGroup {};
            class fnc_cmdDespawnGroup {};
            class fnc_cmdCreateRoadblock {};
            class fnc_cmdCallCas {};
            class fnc_cmdSetAlertLevel {};
            class fnc_cmdSetPriority {};
        };
    };
};
