# Tools

Development utilities for testing and debugging the GM system without Arma 3.

## mock_arma_client.py

Emulates the Arma 3 SQF layer: sends game state to the GM server and prints the returned commands. Use this to test the server without launching Arma.

### Prerequisites

```bash
pip install httpx  # or: pip install -e gm-server/
```

### Usage

```bash
# Interactive mode
python tools/mock_arma_client.py --url http://localhost:8080

# Auto mode: sends a tick every N seconds automatically
python tools/mock_arma_client.py --url http://localhost:8080 --auto
python tools/mock_arma_client.py --url http://localhost:8080 --auto --interval 5

# Custom state file
python tools/mock_arma_client.py --url http://localhost:8080 \
  --state my_state.json --auto
```

### Interactive commands

| Key | Action |
|-----|--------|
| `Enter` | Send one tick with the loaded state |
| `d` | Send an operator directive (prompts for text and priority) |
| `o` | Send a direct command override (prompts for JSON) |
| `s` | Show current server status |
| `q` | Quit |

### Default state file

`gm-server/src/gm_server/tests/fixtures/sample_state.json` — an Agia Marina scenario with 5 OPFOR units, 2 enemy contacts, 3 objectives, and recent events.

You can edit this file or create your own to test specific scenarios.

### Example output

```
[Tick 15] Sent. Response:
  commands (2):
    [HIGH] move_squad: grp_bravo_1 → agia_marina_road_south
           "Enemy approaching from south, intercept with reserve"
    [NORMAL] set_behaviour: grp_alpha_1 (combat/red)
           "Crossroad under direct threat, increase readiness"
```

---

## graph_visualizer.py

Renders a map graph JSON file as a 2D plot using networkx and matplotlib. Useful for verifying graph structure and debugging node positions.

### Prerequisites

```bash
pip install networkx matplotlib
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
