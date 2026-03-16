import logging

from gm_server.graph.context_builder import ContextBuilder
from gm_server.llm.client import LLMClient
from gm_server.llm.prompt_builder import PromptBuilder
from gm_server.llm.response_parser import parse_response
from gm_server.logic.pacing import PacingFSM
from gm_server.logic.state_manager import StateManager
from gm_server.logic.validator import Validator
from gm_server.models.commands import TickResponse
from gm_server.models.game_state import GameState

logger = logging.getLogger(__name__)


class DecisionLoop:
    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder,
        state_manager: StateManager,
        validator: Validator,
        pacing: PacingFSM,
        context_builder: ContextBuilder,
    ):
        self.llm = llm_client
        self.prompt_builder = prompt_builder
        self.state_manager = state_manager
        self.validator = validator
        self.pacing = pacing
        self.context_builder = context_builder
        self.last_raw_response: str = ""
        self.tick_log: list[dict] = []

    async def process_tick(self, game_state: GameState) -> TickResponse:
        """Main tick: state -> LLM -> commands."""
        tick_id = game_state.tick_id
        logger.info("Processing tick %d (mission_time=%.1f)", tick_id, game_state.mission_time)

        # 1. Update state from Arma data
        self.state_manager.update_from_game_state(game_state)

        # 2. Tick directives (decrement TTL)
        self.state_manager.tick_directives()

        # 3. Check if paused
        if self.state_manager.state.paused:
            overrides = self.state_manager.pop_overrides()
            if overrides:
                self.state_manager.apply_orders(overrides)
                return TickResponse(tick_id=tick_id, commands=overrides)
            return TickResponse(tick_id=tick_id)

        # 4. Check override queue
        overrides = self.state_manager.pop_overrides()
        if overrides:
            validated = self.validator.validate(overrides)
            self.state_manager.apply_orders(validated)
            self._log_tick(tick_id, validated, "operator_override", "")
            return TickResponse(tick_id=tick_id, commands=validated)

        # 5. Update pacing
        contacts = len(game_state.enemy_contacts)
        casualties = sum(
            1
            for e in game_state.events_since_last_tick
            if e.type.value in ("unit_killed", "unit_damaged")
        )
        contested = sum(1 for o in game_state.objectives if o.status.value == "contested")
        self.pacing.update(contacts, casualties, contested, len(game_state.events_since_last_tick))

        # 6. Build graph context
        graph_context = self.context_builder.build_context(game_state)

        # 7. Build prompt
        system_prompt, user_prompt = self.prompt_builder.build(
            self.state_manager,
            graph_context,
            self.pacing.info,
            self.state_manager.state.directives,
        )

        # 8. Call LLM
        raw_response = await self.llm.generate(user_prompt, system_prompt)
        self.last_raw_response = raw_response

        if not raw_response:
            logger.warning("Empty LLM response for tick %d, holding positions", tick_id)
            self._log_tick(tick_id, [], "llm_empty", "")
            return TickResponse(tick_id=tick_id)

        # 9. Parse response
        tick_response = parse_response(raw_response, tick_id)

        # 10. Validate commands
        validated = self.validator.validate(tick_response.commands)

        # 11. Apply orders to state
        self.state_manager.apply_orders(validated)

        self._log_tick(tick_id, validated, "llm", raw_response)
        logger.info("Tick %d: %d commands issued", tick_id, len(validated))

        return TickResponse(tick_id=tick_id, commands=validated)

    def _log_tick(self, tick_id: int, commands: list, source: str, raw: str) -> None:
        entry = {
            "tick_id": tick_id,
            "source": source,
            "commands": [
                {"type": c.type, "params": c.params, "reasoning": c.reasoning} for c in commands
            ],
            "raw_response": raw[:500] if raw else "",
        }
        self.tick_log.append(entry)
        # Keep last 20
        if len(self.tick_log) > 20:
            self.tick_log = self.tick_log[-20:]
