#!/usr/bin/env python3
"""Mock Arma 3 client for testing the GM server.

Simulates game ticks for an Agia Marina defense scenario.
Sends tick data to the GM server and displays responses.

Usage:
    python tools/mock_arma_client.py [--url http://localhost:8080]
"""

import argparse
import copy
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


# --- Initial scenario state ---

INITIAL_FORCES = [
    {
        "id": "grp_alpha_1",
        "type": "infantry_squad",
        "size": 8,
        "position": "agia_marina_crossroad",
        "status": "defending",
        "health": 1.0,
        "ammo": 1.0,
        "current_task": "defend crossroad",
    },
    {
        "id": "grp_alpha_2",
        "type": "infantry_squad",
        "size": 8,
        "position": "agia_marina_church",
        "status": "defending",
        "health": 1.0,
        "ammo": 1.0,
        "current_task": "defend church square",
    },
    {
        "id": "grp_bravo_1",
        "type": "infantry_squad",
        "size": 8,
        "position": "agia_marina_east",
        "status": "defending",
        "health": 1.0,
        "ammo": 1.0,
        "current_task": "defend eastern flank",
    },
    {
        "id": "grp_bravo_2",
        "type": "infantry_squad",
        "size": 8,
        "position": "agia_marina_south",
        "status": "defending",
        "health": 1.0,
        "ammo": 1.0,
        "current_task": "defend southern approach",
    },
    {
        "id": "grp_motor_1",
        "type": "motorized",
        "size": 4,
        "position": "agia_marina_warehouse",
        "status": "idle",
        "health": 1.0,
        "ammo": 1.0,
        "current_task": "",
    },
]

INITIAL_CONTACTS = [
    {
        "id": "contact_1",
        "type": "infantry",
        "estimated_size": "squad",
        "position": "agia_marina_road_south",
        "confidence": 0.7,
        "direction": "approaching",
        "last_seen": None,
    },
    {
        "id": "contact_2",
        "type": "infantry",
        "estimated_size": "squad",
        "position": "agia_marina_road_south",
        "confidence": 0.5,
        "direction": "approaching",
        "last_seen": None,
    },
]

INITIAL_OBJECTIVES = [
    {
        "id": "obj_crossroad",
        "status": "held",
        "threat_level": "medium",
        "graph_node": "agia_marina_crossroad",
    },
    {
        "id": "obj_church",
        "status": "held",
        "threat_level": "low",
        "graph_node": "agia_marina_church",
    },
    {
        "id": "obj_market",
        "status": "held",
        "threat_level": "low",
        "graph_node": "agia_marina_market",
    },
]

INITIAL_RESOURCES = {
    "reserve_infantry": 2,
    "reserve_motorized": 1,
    "artillery_available": True,
    "cas_available": False,
}

# Contact approach path (south to center)
CONTACT_PATH = [
    "agia_marina_road_south",
    "agia_marina_south",
    "agia_marina_bridge",
    "agia_marina_gas_station",
    "agia_marina_parking",
    "agia_marina_crossroad",
]


class MockState:
    """Mutable mock game state."""

    def __init__(self):
        self.tick_id = 0
        self.mission_time = 0.0
        self.forces = copy.deepcopy(INITIAL_FORCES)
        self.contacts = copy.deepcopy(INITIAL_CONTACTS)
        self.objectives = copy.deepcopy(INITIAL_OBJECTIVES)
        self.resources = copy.deepcopy(INITIAL_RESOURCES)
        self.events: list[dict] = []
        self.contact_step = 0  # how far contacts have advanced

    def advance_tick(self):
        """Advance the simulation by one tick."""
        self.tick_id += 1
        self.mission_time += 15.0  # 15 seconds per tick
        self.events = []

        # Move contacts closer every 2 ticks
        if self.tick_id % 2 == 0 and self.contact_step < len(CONTACT_PATH) - 1:
            self.contact_step += 1
            new_pos = CONTACT_PATH[self.contact_step]
            for c in self.contacts:
                c["position"] = new_pos
                c["confidence"] = min(1.0, c["confidence"] + 0.1)
                c["last_seen"] = self.mission_time
            self.events.append({
                "type": "contact_new",
                "data": {"position": new_pos, "count": len(self.contacts)},
                "timestamp": self.mission_time,
            })

            # Increase threat on crossroad as contacts approach
            if self.contact_step >= 2:
                for obj in self.objectives:
                    if obj["id"] == "obj_crossroad":
                        obj["threat_level"] = "high"
                        obj["status"] = "contested" if self.contact_step >= 4 else "held"

        # Simulate gradual ammo depletion for units in combat
        if self.contact_step >= 3:
            for force in self.forces:
                if force["status"] in ("defending", "combat"):
                    force["ammo"] = max(0.1, force["ammo"] - 0.05)
                    if force["position"] == CONTACT_PATH[self.contact_step]:
                        force["status"] = "combat"
                        force["health"] = max(0.3, force["health"] - 0.1)
                        if force["health"] < 0.5:
                            force["size"] = max(3, force["size"] - 1)
                            self.events.append({
                                "type": "unit_damaged",
                                "data": {"unit": force["id"], "health": force["health"]},
                                "timestamp": self.mission_time,
                            })

    def apply_commands(self, commands: list[dict]):
        """Apply received GM commands to mock state."""
        for cmd in commands:
            cmd_type = cmd.get("type", "")
            params = cmd.get("params", {})
            unit_id = params.get("unit", "")

            force = next((f for f in self.forces if f["id"] == unit_id), None)

            if cmd_type == "move_squad" and force:
                dest = params.get("to", "")
                force["position"] = dest
                force["status"] = "moving"
                force["current_task"] = f"moving to {dest}"

            elif cmd_type == "position_squad" and force:
                loc = params.get("location", "")
                force["position"] = loc
                force["status"] = "defending"
                force["current_task"] = f"defending {loc}"

            elif cmd_type == "retreat" and force:
                fb = params.get("fallback_position", "")
                force["position"] = fb
                force["status"] = "retreating"
                force["current_task"] = f"retreating to {fb}"

            elif cmd_type == "move_vehicle" and force:
                dest = params.get("to", "")
                force["position"] = dest
                force["status"] = "moving"
                force["current_task"] = f"moving to {dest}"

            elif cmd_type == "set_fortify" and force:
                loc = params.get("location", "")
                force["position"] = loc
                force["status"] = "defending"
                force["current_task"] = f"fortifying {loc}"

            elif cmd_type == "set_overwatch" and force:
                loc = params.get("location", "")
                force["position"] = loc
                force["status"] = "defending"
                force["current_task"] = f"overwatch at {loc}"

            elif cmd_type == "reinforce":
                reserve_type = params.get("from_reserve", "infantry")
                dest = params.get("to", "unknown")
                comp = params.get("composition", "infantry_squad")
                if reserve_type == "infantry" and self.resources["reserve_infantry"] > 0:
                    self.resources["reserve_infantry"] -= 1
                    new_id = f"grp_reinf_{self.tick_id}"
                    self.forces.append({
                        "id": new_id,
                        "type": comp,
                        "size": 8,
                        "position": dest,
                        "status": "moving",
                        "health": 1.0,
                        "ammo": 1.0,
                        "current_task": f"reinforcing {dest}",
                    })
                elif reserve_type == "motorized" and self.resources["reserve_motorized"] > 0:
                    self.resources["reserve_motorized"] -= 1
                    new_id = f"grp_reinf_m_{self.tick_id}"
                    self.forces.append({
                        "id": new_id,
                        "type": "motorized",
                        "size": 4,
                        "position": dest,
                        "status": "moving",
                        "health": 1.0,
                        "ammo": 1.0,
                        "current_task": f"reinforcing {dest}",
                    })

            elif cmd_type == "artillery_strike":
                target = params.get("target_node", "unknown")
                self.events.append({
                    "type": "objective_changed",
                    "data": {"note": f"Artillery strike on {target}"},
                    "timestamp": self.mission_time,
                })

            elif cmd_type == "set_ambush":
                for uid in params.get("units", []):
                    f = next((f for f in self.forces if f["id"] == uid), None)
                    if f:
                        loc = params.get("location", f["position"])
                        f["position"] = loc
                        f["status"] = "defending"
                        f["current_task"] = f"ambush at {loc}"

    def to_game_state(self) -> dict:
        """Build GameState payload for the server."""
        return {
            "tick_id": self.tick_id,
            "mission_time": self.mission_time,
            "friendly_forces": self.forces,
            "enemy_contacts": self.contacts,
            "objectives": self.objectives,
            "events_since_last_tick": self.events,
            "resources": self.resources,
            "graph": {"strategic": {}, "tactical": {}, "local": None},
            "pacing": {
                "current_phase": "calm",
                "intensity": 0.0,
                "phase_ticks": 0,
            },
        }


def print_divider(char="-", width=80):
    print(char * width)


def print_header(text):
    print_divider("=")
    print(f"  {text}")
    print_divider("=")


def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def print_state(state: MockState):
    """Display current mock state."""
    print(f"\n  Tick: {state.tick_id}  |  Mission Time: {format_time(state.mission_time)}")
    print_divider()

    # Forces
    print("  FORCES:")
    fmt = "    {:<16} {:<16} {:<12} {:<28} {:>4}  {:>5}  {:>5}"
    print(fmt.format("ID", "Type", "Status", "Position", "Size", "HP", "Ammo"))
    print_divider("-", 100)
    for f in state.forces:
        hp_str = f"{f['health']:.0%}"
        ammo_str = f"{f['ammo']:.0%}"
        print(fmt.format(
            f["id"], f["type"], f["status"],
            f["position"], str(f["size"]), hp_str, ammo_str,
        ))

    # Contacts
    print("\n  CONTACTS:")
    for c in state.contacts:
        conf_str = f"{c['confidence']:.0%}"
        print(f"    {c['id']}: {c['type']} ({c['estimated_size']}) "
              f"at {c['position']} [{c['direction']}] conf={conf_str}")

    # Objectives
    print("\n  OBJECTIVES:")
    for o in state.objectives:
        indicator = {"low": ".", "medium": "*", "high": "!", "critical": "!!!"}
        threat_char = indicator.get(o["threat_level"], "?")
        print(f"    {o['id']}: {o['status']} (threat: {o['threat_level']} {threat_char})")

    # Resources
    r = state.resources
    print(f"\n  RESOURCES: infantry_reserve={r['reserve_infantry']} "
          f"motorized_reserve={r['reserve_motorized']} "
          f"artillery={'YES' if r['artillery_available'] else 'NO'} "
          f"CAS={'YES' if r['cas_available'] else 'NO'}")

    # Events
    if state.events:
        print("\n  EVENTS this tick:")
        for e in state.events:
            print(f"    [{e['type']}] {json.dumps(e['data'])}")
    print()


def print_response(resp: dict):
    """Display GM server response."""
    cmds = resp.get("commands", [])
    print(f"  SERVER RESPONSE: {len(cmds)} command(s)")
    print_divider()
    if not cmds:
        print("    (no commands)")
    for cmd in cmds:
        reasoning = cmd.get("reasoning", "")
        print(f"    CMD: {cmd.get('type', '?')}")
        print(f"         params: {json.dumps(cmd.get('params', {}))}")
        if reasoning:
            print(f"         reason: {reasoning}")
    print()


def send_directive(client: httpx.Client, base_url: str):
    """Interactive: send an operator directive."""
    text = input("  Directive text: ").strip()
    if not text:
        print("  (cancelled)")
        return
    priority = input("  Priority [low/normal/high/critical] (default: normal): ").strip() or "normal"
    ttl = input("  TTL ticks (default: 10): ").strip()
    ttl_val = int(ttl) if ttl.isdigit() else 10

    try:
        r = client.post(f"{base_url}/api/v1/directive", json={
            "text": text, "priority": priority, "ttl_ticks": ttl_val,
        })
        print(f"  -> {r.json()}")
    except Exception as e:
        print(f"  ERROR: {e}")


def send_override(client: httpx.Client, base_url: str):
    """Interactive: send override commands."""
    print("  Enter commands JSON (single line):")
    raw = input("  > ").strip()
    if not raw:
        print("  (cancelled)")
        return
    try:
        parsed = json.loads(raw)
        cmds = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON: {e}")
        return

    try:
        r = client.post(f"{base_url}/api/v1/override", json={"commands": cmds})
        print(f"  -> {r.json()}")
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Mock Arma 3 client for GM server testing")
    parser.add_argument("--url", type=str, default="http://localhost:8080",
                        help="GM server base URL (default: http://localhost:8080)")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-advance ticks (no interactive input)")
    parser.add_argument("--ticks", type=int, default=20,
                        help="Number of ticks in auto mode (default: 20)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between auto ticks in seconds (default: 2.0)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    state = MockState()

    print_header("ARMA 3 GM -- MOCK CLIENT")
    print(f"  Server: {base_url}")
    print(f"  Scenario: Agia Marina Defense")
    print(f"  OPFOR: 4 infantry squads + 1 motorized defending town")
    print(f"  BLUFOR: 2 infantry squads approaching from south")
    print()

    if not args.auto:
        print("  Controls:")
        print("    Enter = next tick")
        print("    d     = send directive")
        print("    o     = send override")
        print("    s     = show status (GET /api/v1/status)")
        print("    p     = pause GM")
        print("    r     = resume GM")
        print("    q     = quit")
        print()

    client = httpx.Client(timeout=30.0)

    # Check server connectivity
    try:
        r = client.get(f"{base_url}/api/v1/status")
        print(f"  Server connected. Status: {r.status_code}")
    except httpx.ConnectError:
        print(f"  WARNING: Cannot connect to {base_url}. Start the server first.")
        if not args.auto:
            print("  Continuing anyway (will retry on each tick)...")
        else:
            print("  Exiting.")
            sys.exit(1)

    print_divider("=")

    tick_count = 0
    while True:
        if args.auto:
            if tick_count >= args.ticks:
                print("\n  Auto mode complete.")
                break
            time.sleep(args.delay)
        else:
            try:
                user_input = input("[tick] Enter/d/o/s/p/r/q > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Exiting.")
                break

            if user_input == "q":
                print("  Exiting.")
                break
            elif user_input == "d":
                send_directive(client, base_url)
                continue
            elif user_input == "o":
                send_override(client, base_url)
                continue
            elif user_input == "s":
                try:
                    r = client.get(f"{base_url}/api/v1/status")
                    print(json.dumps(r.json(), indent=2))
                except Exception as e:
                    print(f"  ERROR: {e}")
                continue
            elif user_input == "p":
                try:
                    r = client.post(f"{base_url}/api/v1/control", json={"action": "pause"})
                    print(f"  -> {r.json()}")
                except Exception as e:
                    print(f"  ERROR: {e}")
                continue
            elif user_input == "r":
                try:
                    r = client.post(f"{base_url}/api/v1/control", json={"action": "resume"})
                    print(f"  -> {r.json()}")
                except Exception as e:
                    print(f"  ERROR: {e}")
                continue

        # Advance simulation
        prev_state = {f["id"]: copy.deepcopy(f) for f in state.forces}
        state.advance_tick()
        tick_count += 1

        # Show state
        print_state(state)

        # Show diffs
        diffs = []
        for f in state.forces:
            prev = prev_state.get(f["id"])
            if not prev:
                diffs.append(f"  + NEW UNIT: {f['id']} at {f['position']}")
                continue
            changes = []
            for key in ("position", "status", "health", "ammo", "size"):
                if f[key] != prev[key]:
                    changes.append(f"{key}: {prev[key]} -> {f[key]}")
            if changes:
                diffs.append(f"  ~ {f['id']}: {', '.join(changes)}")
        if diffs:
            print("  STATE CHANGES:")
            for d in diffs:
                print(f"    {d}")
            print()

        # Send tick to server
        payload = state.to_game_state()
        try:
            r = client.post(f"{base_url}/api/v1/tick", json=payload)
            if r.status_code == 200:
                resp = r.json()
                print_response(resp)
                # Apply commands to mock state
                state.apply_commands(resp.get("commands", []))
            else:
                print(f"  SERVER ERROR {r.status_code}: {r.text[:200]}")
        except httpx.ConnectError:
            print(f"  CONNECTION FAILED: Cannot reach {base_url}")
        except Exception as e:
            print(f"  ERROR: {e}")

        print_divider()

    client.close()


if __name__ == "__main__":
    main()
