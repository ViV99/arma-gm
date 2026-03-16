from __future__ import annotations

from gm_server.graph.model import MapGraph


def serialize_strategic(graph: MapGraph) -> str:
    """Serialize L0 strategic graph to compact tactical text (~200 tokens)."""
    lines = ["=== STRATEGIC OVERVIEW ==="]
    for node in sorted(graph.nodes.values(), key=lambda n: n.name):
        props = node.properties
        suitability = ", ".join(props.get("tactical_suitability", []))
        cover = props.get("cover_quality", 0)
        dominance = props.get("dominance", 0)
        vehicle = "vehicles OK" if props.get("vehicle_access") else "infantry only"
        lines.append(
            f"- {node.name} ({node.id}): elev {node.elevation:.0f}m, "
            f"cover {cover:.1f}, dominance {dominance:.1f}, {vehicle}"
            f"{f', suitable for: {suitability}' if suitability else ''}"
        )

    lines.append("\nRoutes:")
    for edge in graph.edges:
        road = edge.road_type if edge.road_type != "none" else "off-road"
        veh = "" if edge.vehicle_traversable else " [NO VEHICLES]"
        lines.append(
            f"- {edge.from_node} -> {edge.to_node}: {edge.distance:.0f}m, "
            f"{road}, cover {edge.cover_rating:.1f}{veh}"
        )

    return "\n".join(lines)


def serialize_tactical(graph: MapGraph, zone_name: str) -> str:
    """Serialize L1 tactical graph to detailed tactical text (~300 tokens per zone)."""
    lines = [f"=== TACTICAL VIEW: {zone_name.upper().replace('_', ' ')} ==="]

    for node in sorted(graph.nodes.values(), key=lambda n: n.name):
        props = node.properties
        details = []
        if props.get("building_count", 0) > 0:
            details.append(f"{props['building_count']} buildings")
        cover = props.get("cover_quality", 0)
        details.append(f"cover {cover:.1f}")
        suitability = props.get("tactical_suitability", [])
        if suitability:
            details.append(f"good for: {', '.join(suitability)}")
        lines.append(f"- {node.name} ({node.id}): {', '.join(details)}")

    lines.append("\nMovement routes:")
    for edge in graph.edges:
        road = edge.road_type if edge.road_type != "none" else "open ground"
        veh = "" if edge.vehicle_traversable else " [FOOT ONLY]"
        lines.append(
            f"- {edge.from_node} -> {edge.to_node}: {edge.distance:.0f}m, "
            f"{road}, cover {edge.cover_rating:.1f}{veh}"
        )

    return "\n".join(lines)


def serialize_local(graph: MapGraph, center_node: str = "") -> str:
    """Serialize L2 local graph to detailed building/cover text."""
    header = f"=== LOCAL DETAIL: {center_node.upper().replace('_', ' ')} ===" if center_node else "=== LOCAL DETAIL ==="
    lines = [header]
    for node in graph.nodes.values():
        props = node.properties
        details = []
        if "floors" in props:
            details.append(f"{props['floors']} floors")
        if "windows_facing" in props:
            details.append(f"windows facing {props['windows_facing']}")
        if "cover_type" in props:
            details.append(props["cover_type"])
        cover = props.get("cover_quality", 0)
        details.append(f"cover {cover:.1f}")
        suitability = props.get("tactical_suitability", [])
        if suitability:
            details.append(f"good for: {', '.join(suitability)}")
        lines.append(f"- {node.name} ({node.id}): {', '.join(details)}")

    if graph.edges:
        lines.append("\nApproaches:")
        for edge in graph.edges:
            veh = "" if edge.vehicle_traversable else " [FOOT ONLY]"
            lines.append(
                f"- {edge.from_node} -> {edge.to_node}: {edge.distance:.0f}m, "
                f"cover {edge.cover_rating:.1f}{veh}"
            )
    return "\n".join(lines)
