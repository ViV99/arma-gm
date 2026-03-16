# Tools

Development utilities for testing and debugging the GM system without Arma 3.

## mock_arma_client.py

Emulates the Arma 3 SQF layer: sends game state to the GM server and prints the returned commands. Use this to test the server without launching Arma.

### Prerequisites

`httpx` is a dependency of `gm-server`. Install it by setting up the GM server venv:

```bash
cd gm-server
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Then run the mock client from that activated environment.

### Usage

```bash
# Interactive mode
python tools/mock_arma_client.py --url http://localhost:8080

# Auto mode: run 20 ticks with 2 s delay (defaults)
python tools/mock_arma_client.py --url http://localhost:8080 --auto

# Custom number of ticks and delay
python tools/mock_arma_client.py --url http://localhost:8080 --auto --ticks 30 --delay 5
```

### Interactive commands

| Key | Action |
|-----|--------|
| `Enter` | Send one tick |
| `d` | Send an operator directive (prompts for text and priority) |
| `o` | Send a direct command override (prompts for JSON) |
| `s` | Show current server status |
| `p` | Pause GM decision-making |
| `r` | Resume GM decision-making |
| `q` | Quit |

The scenario (Agia Marina defense with 4 OPFOR squads + 1 motorized vs 2 BLUFOR squads) is hardcoded in the script. Edit `INITIAL_FORCES` / `INITIAL_OBJECTIVES` at the top of the file to customise.

### Example output

```
  SERVER RESPONSE: 2 command(s)
────────────────────────────────────────────────
    CMD: move_squad
         params: {"unit": "grp_bravo_1", "to": "agia_marina_road_south", "task": "intercept"}
         reason: Enemy squad approaching from south, send reserve to intercept
    CMD: set_behaviour
         params: {"unit": "grp_alpha_1", "behaviour": "COMBAT", "combat_mode": "RED"}
         reason: Crossroad under direct threat, increase readiness
```

---

## graph_visualizer.py

Renders a map graph JSON file as a 2D plot using networkx and matplotlib. Useful for verifying graph structure and debugging node positions.

### Prerequisites

```bash
cd tools && poetry install
```

### Usage

```bash
# Display interactively
python tools/graph_visualizer.py shared/maps/stratis/strategic_graph.json

# Save to PNG (good for documentation)
python tools/graph_visualizer.py shared/maps/stratis/tactical/agia_marina.json \
  --output agia_marina.png

# Custom title
python tools/graph_visualizer.py shared/maps/stratis/strategic_graph.json \
  --title "Stratis L0"
```

### Visual encoding

**Node colors** indicate type:

| Color | Type |
|-------|------|
| Blue | `town`, `intersection` |
| Red | `military` |
| Green | `terrain`, `open_area` |
| Orange | `entry_point`, `approach` |
| Purple | `landing_zone` |
| Gold | `landmark` |
| Grey | unknown type |

**Edge thickness and color** indicate road type:

| | `main` | `secondary` | `dirt` | `path` | `none` |
|-|--------|-------------|--------|--------|--------|
| Width | 3.0 | 2.0 | 1.5 | 1.0 | 0.5 |
| Color | Yellow | Light yellow | Brown | Dark green | Dark grey |

The plot uses Arma world coordinates (x = easting, z = northing in Arma = y on the plot). Node labels show the node name.
