# Arma Mod (@ArmaGM)

The Arma 3 addon that collects game state, executes GM commands, and runs the City Defense mission. Built with [HEMTT](https://github.com/BrettMayson/HEMTT).

## What It Does

- Every 15 seconds: collects all unit positions, contacts, objectives, and events, sends to GM server
- Receives commands via `ExtensionCallback` and dispatches them to per-command executors
- Tracks dynamic graph changes (building destroyed → cover update)
- Generates L2 local graphs on demand (`request_intel` command)

## Building

Requires [HEMTT](https://github.com/BrettMayson/HEMTT):

```bash
cd arma-mod
hemtt build
# Output: .hemtt/release/@ArmaGM/
```

Or for development (no signing, no pbo):

```bash
hemtt dev
```

## Installing

Copy `.hemtt/release/@ArmaGM/` to your Arma 3 mods folder and load with `-mod=@ArmaGM`.

The extension DLL (`arma_gm_ext_x64.dll`) must be in the Arma 3 root directory (see [`arma-extension/README.md`](../arma-extension/README.md)).

## Configuration

In the mission's `init.sqf`, set these variables **before** the addon initialises:

```sqf
// URL of the GM server (default: http://127.0.0.1:8080)
ArmaGM_serverUrl = "http://192.168.1.10:8080";

// Seconds between GM ticks (default: 15)
ArmaGM_tickInterval = 15;
```

These are read by `fnc_init.sqf` during `preInit`.

## Mission: ArmaGM_CityDefense.Stratis

A 1–4 player co-op mission. BLUFOR (players) must capture 3 control zones in Agia Marina. OPFOR (LLM) defends with 5 groups and limited reserves.

**Starting setup:**
- `grp_alpha_1` — 8 infantry at the crossroad (defending)
- `grp_bravo_1` — 8 infantry at the church (reserve)
- `grp_charlie_1` — 8 infantry at the warehouse (western sector)
- `grp_delta_1` — 4 snipers at the tower (overwatch)
- `grp_motor_1` — 3 motorized at the parking area (mobile reaction force)
- 2 off-map infantry reserves, 1 motorized reserve, artillery available

**Objectives:**
- `obj_crossroad` — Agia Marina crossroad
- `obj_church` — Church square
- `obj_warehouse` — Western warehouse

**End conditions:**
- BLUFOR wins if all 3 objectives are lost by OPFOR
- OPFOR wins if all BLUFOR are eliminated

## SQF Function Reference

All functions are registered under tag `ArmaGM` (e.g. `ArmaGM_fnc_init`).

### Core Tick Loop

| Function | Description |
|----------|-------------|
| `fnc_init` | `preInit` — registers EHs, configures extension, spawns tick loop |
| `fnc_tick` | `while {true}` loop, calls `fnc_collectState` every tick interval |
| `fnc_collectState` | Builds full GameState JSON, calls `fnc_sendState` |
| `fnc_sendState` | `callExtension ["send_state", [_json]]` |
| `fnc_receiveCommands` | Handles ExtensionCallback — chunking, JSON parse, dispatch |
| `fnc_executeCommand` | Dispatches parsed command hashmap to per-type handler |

### Command Executors

| Function | Command | Key Params |
|----------|---------|-----------|
| `fnc_cmdMoveSquad` | `move_squad` | unit, to, task, speed |
| `fnc_cmdPositionSquad` | `position_squad` | unit, location, task, sector |
| `fnc_cmdSetBehaviour` | `set_behaviour` | unit, behaviour, combat_mode |
| `fnc_cmdReinforce` | `reinforce` | from_reserve, to, composition |
| `fnc_cmdRetreat` | `retreat` | unit, fallback_position |
| `fnc_cmdArtilleryStrike` | `artillery_strike` | target_node, rounds |
| `fnc_cmdSetAmbush` | `set_ambush` | unit, location, trigger_zone |
| `fnc_cmdSetFortify` | `set_fortify` | unit, location |
| `fnc_cmdSetPatrol` | `set_patrol` | unit, route_nodes |
| `fnc_cmdSetOverwatch` | `set_overwatch` | unit, location, watch_sector |
| `fnc_cmdSpawnGroup` | `spawn_group` | composition, location, task |
| `fnc_cmdDespawnGroup` | `despawn_group` | unit, reason |
| `fnc_cmdCreateRoadblock` | `create_roadblock` | location, unit |
| `fnc_cmdCallCas` | `call_cas` | target_node, type |
| `fnc_cmdSetAlertLevel` | `set_alert_level` | level |
| `fnc_cmdSetPriority` | `set_priority` | objective, priority |

### Graph & Map

| Function | Description |
|----------|-------------|
| `fnc_nearestNode` | Given `[x,y,z]`, returns nearest node ID from `ArmaGM_nodePositions` |
| `fnc_graphExtract` | Scans buildings/cover in radius around a node, returns L2 graph JSON |
| `fnc_graphUpdate` | Writes a property override to `ArmaGM_nodeUpdates` hashmap |

### Events

| Function | Description |
|----------|-------------|
| `fnc_eventKilled` | Checks objectives after a kill, updates contested status |
| `fnc_eventContact` | Adds `contact_new` event to `ArmaGM_events` buffer |

## Global State Variables

These globals are managed by the addon and read during state collection:

| Variable | Type | Description |
|----------|------|-------------|
| `ArmaGM_tickId` | Number | Current tick counter |
| `ArmaGM_groups` | Array `[[id, group], ...]` | All managed OPFOR groups |
| `ArmaGM_objectives` | Array `[[id, status, threat, node], ...]` | Objective states |
| `ArmaGM_contacts` | Array `[[id, type, size, node, conf, dir, time], ...]` | Manual contacts |
| `ArmaGM_events` | Array `[[type, dataJson, time], ...]` | Event buffer, flushed each tick |
| `ArmaGM_reserves` | Array `[inf, mot, artBool, casBool]` | Available reserves |
| `ArmaGM_nodePositions` | Array `[[id, [x,y]], ...]` | Node positions (set by mission) |
| `ArmaGM_nodeUpdates` | HashMap `{nodeId: {prop: val}}` | Dynamic property overrides |
| `ArmaGM_intelNode` | String | Node to extract L2 for on next tick |
| `ArmaGM_chunkBuffer` | Array | Chunked response assembly buffer |

## Creating a Custom Mission

1. Copy `missions/ArmaGM_CityDefense.Stratis/` as a starting point
2. In `initServer.sqf`, populate `ArmaGM_nodePositions` with node IDs and `[x, y]` coordinates matching your tactical graph JSON
3. Edit `scripts/setupDefenders.sqf` to spawn your OPFOR units and register them in `ArmaGM_groups`
4. Edit `scripts/setupObjectives.sqf` to define control zones
5. Set `ArmaGM_serverUrl` in `init.sqf` if the server isn't on localhost

Node positions must match the IDs in `shared/maps/<map>/tactical/<zone>.json`. Use `tools/graph_visualizer.py` to inspect the graphs.

## Adding a New Command

1. Create `fnc_cmdYourCommand.sqf` in `addons/main/functions/`
2. Add `class fnc_cmdYourCommand {};` to `config.cpp` in `class Main`
3. Add a `case "your_command": { [_params] call ArmaGM_fnc_cmdYourCommand };` in `fnc_executeCommand.sqf`
4. Add the command type and its Pydantic params model to `gm-server/src/gm_server/models/commands.py`
5. Update `COMMAND_PARAMS_MAP` in the same file
