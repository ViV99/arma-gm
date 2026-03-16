# Arma 3 LLM Game Master

An LLM-based Game Master for Arma 3 that replaces the human Zeus operator. Controls OPFOR forces strategically in real time — adapts to player tactics, manages pacing, and creates an engaging PvE experience. The LLM acts as a military commander, not a micromanager of individual units.

## Architecture

```
Arma 3 (SQF)  ←→  Extension DLL (Rust)  ←→  GM Server (Python)  ←→  Local LLM (Ollama)
   collect            async HTTP                  state mgmt
   state              callExtension               pacing FSM
   execute            chunking                    graph context
   commands           callbacks                   prompt build
```

The LLM decides **strategy** (where to attack, when to commit reserves, how to adapt). The built-in Arma AI handles **tactics** (pathfinding, engagement, cover, formations). SQF translates LLM commands into waypoints and Arma orders.

## Components

| Directory | Language | Role |
|-----------|----------|------|
| [`gm-server/`](gm-server/README.md) | Python | GM server — state management, LLM integration, API |
| [`arma-extension/`](arma-extension/README.md) | Rust | Extension DLL — async bridge between SQF and GM server |
| [`arma-mod/`](arma-mod/README.md) | SQF | Arma addon + mission — state collection, command execution |
| [`shared/`](shared/README.md) | JSON | Schemas and map graphs (source of truth) |
| [`tools/`](tools/README.md) | Python | Dev utilities — mock client, graph visualizer |

## Prerequisites

- **Python 3.11+** with pip
- **Ollama** with a 13B–30B model (e.g. `qwen2.5:14b`, `mistral:13b`, `llama3:13b`)
- **Arma 3** (Windows) with the mod loaded for in-game use
- **Rust + cargo** + `mingw-w64` for building the extension DLL on macOS

## Quick Start (GM Server only, no Arma)

```bash
# 1. Start Ollama with a model
ollama pull qwen2.5:14b
ollama serve

# 2. Install and start the GM server
cd gm-server
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m gm_server.main --port 8080

# 3. Test with the mock client
python tools/mock_arma_client.py --url http://localhost:8080 --auto
```

Open `http://localhost:8080/ui` for the operator console.

## Quick Start (Full stack with Arma 3)

```bash
# 1. Start Ollama + GM server (see above)

# 2. Build the extension DLL (macOS → Windows)
cd arma-extension
rustup target add x86_64-pc-windows-gnu
brew install mingw-w64
cargo build --release --target x86_64-pc-windows-gnu
# Copy target/x86_64-pc-windows-gnu/release/arma_gm_ext.dll
# to Arma 3 root as arma_gm_ext_x64.dll (and i686 build as arma_gm_ext.dll)

# 3. Install the mod
cd arma-mod
hemtt build   # requires HEMTT: https://github.com/BrettMayson/HEMTT
# Copy .hemtt/release/@ArmaGM to Arma 3 mods

# 4. Launch Arma 3 with -mod=@ArmaGM
# Load mission: ArmaGM_CityDefense.Stratis
```

Edit `arma-mod/missions/ArmaGM_CityDefense.Stratis/init.sqf` to set `ArmaGM_serverUrl` if the GM server is not on localhost.

## Map Graph System

The LLM reasons about **named locations**, not raw coordinates.

```
L0 Strategic  ─  whole map, ~20 nodes  (always in context)
L1 Tactical   ─  per settlement, ~25 nodes  (included for active combat zones)
L2 Local      ─  per block, on-the-fly  (generated on request_intel command)
```

Graphs are stored in `shared/maps/<map>/`. Visualize with:

```bash
python tools/graph_visualizer.py shared/maps/stratis/strategic_graph.json
python tools/graph_visualizer.py shared/maps/stratis/tactical/agia_marina.json --output agia_marina.png
```

## Operator Interface

While the mission runs, you can intervene via:

| Endpoint | Action |
|----------|--------|
| `POST /api/v1/directive` | Add a text directive to the LLM prompt (with TTL in ticks) |
| `POST /api/v1/override` | Send direct commands bypassing LLM |
| `POST /api/v1/control` | Pause / resume LLM decision-making |
| `GET /ui` | Web operator console |

```bash
# Example: focus LLM on northern defense
curl -s -X POST http://localhost:8080/api/v1/directive \
  -H "Content-Type: application/json" \
  -d '{"text":"Focus all forces on the northern approach","priority":"high","ttl_ticks":5}'
```

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 — GM Server | ✅ Done | Python server, LLM client, state manager, pacing FSM |
| 2 — Extension + SQF | ✅ Done | Rust DLL, SQF addon, City Defense mission |
| 3 — Map Graph System | ✅ Done | L2 on-the-fly, dynamic node updates, graph serialization |
| 4 — Integration | ✅ Done | All 16 command executors, full SQF command set |
| 5 — Polish | 🔲 Later | Altis graphs, model benchmarks, session logging, radio chatter |

## Target LLM Models

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5:14b` | 14B | Default, good balance |
| `mistral:13b` | 13B | Fast, slightly weaker strategy |
| `llama3:13b` | 13B | Good JSON compliance |
| `qwen2.5:32b` | 32B | Best quality, needs strong GPU |

7B models are too weak for strategic reasoning. 70B+ are too slow for 15-second ticks.
