# Arma 3 LLM Game Master

## Project Vision
LLM-based Game Master for Arma 3 that replaces human Zeus player. Controls NPC forces strategically, adapts to player tactics, manages pacing, and creates engaging PvE experience. The LLM acts as a military commander/director, not a micromanager of individual units.

## Key Architectural Decisions

### Local LLM
- Use locally deployed LLM (Ollama / llama.cpp server) — no cloud API due to high traffic volume and cost.
- Target model class: 13B-30B (Mistral, Llama 3, Qwen 2.5). 7B too weak for strategy, 70B+ too heavy for real-time.

### Language Stack
- **SQF scripts** — in-game layer: state collection, command execution, event handling.
- **Rust (arma-rs)** — thin Arma extension DLL, async bridge between SQF and GM server. For MVP can use existing HTTP extension instead.
- **Python** — GM server: game state management, LLM interaction, memory, pacing logic.
- Extension DLL must be Windows (32-bit + 64-bit). Python server is platform-independent.

### Three-Layer Architecture
```
Arma 3 (SQF) ←→ Extension DLL (Rust) ←→ GM Server (Python) ←→ Local LLM
```

### Responsibility Split: LLM vs Built-in AI
**LLM (Game Master) decides:**
- Strategy: where to attack, defend, retreat
- Timing: when to commit reserves, when to wait
- Adaptation: reacting to player tactics
- Pacing: intensity management (L4D Director style)
- Narrative: radio chatter, briefings (future)

**LLM does NOT:**
- Control individual soldiers
- Handle pathfinding, shooting, cover
- Count ammo/HP
- Decide low-level movement

**Deterministic SQF layer:**
- Translates LLM intent-based commands into waypoints/orders
- Spawns/despawns units
- Validates LLM commands (resources exist? position valid?)
- Collects and aggregates game state
- Intensity tracking FSM

**Built-in Arma AI:**
- Pathfinding, engagement, cover, formations
- Following waypoints
- Vehicle operation
- Contact reaction

### LLM Command Interface
LLM outputs structured commands (JSON), not free text:
- `position_squad(unit, location, task, sector)`
- `move_squad(unit, to, task, detail)`
- `move_vehicle(unit, to, task, detail)`
- `reinforce(from, to, composition, route)`
- `set_ambush(location, trigger_condition)`
- `artillery_strike(target, delay)`
- `retreat(group, fallback_position)`
- etc. (~15-20 action types for MVP)

### Hierarchical Map Graph
The map is represented as a hierarchical graph with three levels:

**Level 0 — Strategic (whole map):**
- Nodes: towns, bases, key terrain
- Edges: main roads, routes with distance/travel time
- Always included in LLM context (compact)

**Level 1 — Tactical (settlement/area):**
- Nodes: districts, blocks, key intersections
- Edges: streets, paths with cover ratings
- Included for zones with active combat or nearby players

**Level 2 — Local (block/compound):**
- Nodes: buildings, cover positions, approaches
- Generated on-the-fly by SQF when LLM acts in specific area
- Included only for the active decision zone

### Graph Properties
Each node and edge is enriched with spatial/tactical data:
- **Nodes**: elevation, LoS to other nodes, cover quality, tactical suitability (sniper/vehicle/defense), blind spots, vulnerabilities
- **Edges**: distance, bearing, elevation change, route type, cover on route, traversability (foot/vehicle), observation exposure

**Key principle**: SQF computes spatial relationships deterministically (terrainIntersectASL, checkVisibility etc.), LLM receives tactical conclusions in text form. LLM reasons about named locations and their properties, not raw coordinates.

### Dynamic Graph Updates
- Graph is a live data structure, updated by event handlers (building destroyed, road blocked, fortification built)
- Updates are local — only recalculate affected radius (~200m)
- No change history sent to LLM — just current state snapshot of relevant subgraph
- On each GM tick, LLM receives the current actual state of the subgraph at the needed detail level

### Context Management
LLM does not receive the full graph. Context is built adaptively:
- Strategic overview always (~200 tokens)
- Tactical view for combat zones (~300 tokens per zone)
- Local detail only for active decision area
- Inactive zones summarized in one line

### Future Features (not MVP)
- RP dialogues from NPC characters (can use separate lighter model)
- Vision/multimodal: rendered tactical map sent to vision-capable LLM
- Cross-session campaign memory
- Player personality modeling

## Implementation Status

### ✅ Phase 1 — GM Server (complete)
- Pydantic models: GameState, 18 command types, TickResponse
- Ollama async LLM client (httpx), prompt builder, response parser
- State manager (in-memory): UnitRecord, Order, Directive, anti-thrashing
- Pacing FSM: CALM → BUILD_UP → PEAK → RELAX
- Validator: unit/node existence, resource checks, anti-thrash (3-tick cooldown)
- Decision loop: override queue → pacing → context → LLM → validate → apply
- FastAPI server: /tick, /directive, /override, /control, /status, /ui (operator HTML console)
- Static graphs: L0 strategic (20 nodes, 26 edges), L1 Agia Marina (25 nodes, 38 edges)
- Tools: mock_arma_client.py, graph_visualizer.py

### ✅ Phase 2 — Rust Extension + SQF Addon (complete)
- Rust DLL (arma-rs 1.12): config/send_state/ping commands, ureq HTTP, 8 KB chunking
- Cross-compile config for macOS → Windows (mingw-w64)
- SQF addon (14 functions): init, tick loop, state collection, command dispatch
- Command executors: move_squad, position_squad, set_behaviour, reinforce, retreat
- Event handlers: unit killed, contact detection, objective triggers
- Mission: ArmaGM_CityDefense.Stratis — 5 OPFOR groups, 3 objectives, end conditions

### ✅ Phase 3 — Map Graph System (complete)
- MapGraph.with_updates(): dynamic node property overrides (cover_quality, vehicle_traversable…)
- MapGraph.from_dict(): build L2 graph from SQF-generated JSON
- Context builder: applies node_updates to graphs, parses game_state.graph.local as L2
- serialize_local(): L2 graph → LLM text with building details and approaches
- GameState.graph.node_updates: dict transmitted from SQF each tick
- fnc_graphExtract.sqf: on-the-fly L2 generation (building scan → cluster → JSON)
- fnc_graphUpdate.sqf: accumulates dynamic node overrides in ArmaGM_nodeUpdates
- Building destruction EH: auto-degrades cover_quality of nearest node
- request_intel command: LLM requests L2 → extracted on next tick

### 🔲 Phase 4 — Integration + MVP Mission (next)
Remaining command executors (SQF):
- artillery_strike, set_ambush, set_fortify, set_patrol, set_overwatch
- spawn_group, despawn_group, create_roadblock, call_cas, set_alert_level, set_priority

Then: Windows compile + Arma 3 editor test → integration test with mock client → prompt/pacing tuning.

### 🔲 Phase 5 — Polish (post-MVP)
Altis graphs, model benchmarks, session logging/replay, radio chatter, SQLite campaign memory.

## Development Notes
- BattlEye is typically disabled — not a concern
- Developer environment: macOS (M.Skurikhin), deployment target: Windows
- arma-rs is the preferred Rust framework for Arma extensions
- Existing frameworks to consider: Pythia (Python), a3go (Go), Intercept (C++)
- Existing project reference: DCO GPT (file-based IPC, basic NPC dialogues — our architecture is fundamentally different)
