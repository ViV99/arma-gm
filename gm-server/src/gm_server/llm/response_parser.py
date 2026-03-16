import json
import logging
import re

from gm_server.models.commands import COMMAND_TYPES, Command, TickResponse

logger = logging.getLogger(__name__)


def parse_response(raw_text: str, tick_id: int) -> TickResponse:
    """Extract and validate commands from LLM response text."""
    if not raw_text.strip():
        logger.warning("Empty LLM response for tick %d", tick_id)
        return TickResponse(tick_id=tick_id)

    # Try to extract JSON from response
    json_obj = _extract_json(raw_text)
    if json_obj is None:
        logger.warning("No valid JSON found in LLM response for tick %d", tick_id)
        return TickResponse(tick_id=tick_id)

    # Parse commands
    commands = []
    raw_commands = json_obj.get("commands", []) if isinstance(json_obj, dict) else json_obj
    if not isinstance(raw_commands, list):
        logger.warning("Commands field is not a list for tick %d", tick_id)
        return TickResponse(tick_id=tick_id)

    for i, raw_cmd in enumerate(raw_commands):
        try:
            cmd = Command(**raw_cmd)
            # Validate the command type is known
            if cmd.type not in COMMAND_TYPES:
                logger.warning("Unknown command type '%s' at index %d, skipping", cmd.type, i)
                continue
            # Validate params match the command type
            cmd.validated_params()
            commands.append(cmd)
        except Exception as e:
            logger.warning("Invalid command at index %d: %s (data: %s)", i, e, raw_cmd)
            continue

    logger.info(
        "Parsed %d valid commands from %d total for tick %d",
        len(commands),
        len(raw_commands),
        tick_id,
    )
    return TickResponse(tick_id=tick_id, commands=commands)


def _extract_json(text: str) -> dict | list | None:
    """Extract JSON object or array from text, handling various LLM output formats."""
    # Try 1: markdown code block ```json...```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try 2: find JSON object with "commands" key
    match = re.search(r'\{[^{}]*"commands"\s*:\s*\[.*?\]\s*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Try 3: find any JSON object
    for match in re.finditer(r"\{[^{}]*\}|\[.*?\]", text, re.DOTALL):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

    # Try 4: the whole text is JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None
