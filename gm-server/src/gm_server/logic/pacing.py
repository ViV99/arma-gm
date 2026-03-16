import logging

from gm_server.models.game_state import PacingInfo, PacingPhase

logger = logging.getLogger(__name__)


class PacingFSM:
    """Deterministic pacing FSM that controls combat intensity."""

    def __init__(
        self,
        calm_to_buildup: float = 0.3,
        buildup_to_peak: float = 0.7,
        peak_to_relax: float = 0.4,
        relax_to_calm: float = 0.2,
        peak_max_ticks: int = 8,
    ):
        self.thresholds = {
            "calm_to_buildup": calm_to_buildup,
            "buildup_to_peak": buildup_to_peak,
            "peak_to_relax": peak_to_relax,
            "relax_to_calm": relax_to_calm,
        }
        self.peak_max_ticks = peak_max_ticks
        self.phase = PacingPhase.CALM
        self.intensity = 0.0
        self.phase_ticks = 0

    @property
    def info(self) -> PacingInfo:
        return PacingInfo(
            current_phase=self.phase,
            intensity=self.intensity,
            phase_ticks=self.phase_ticks,
        )

    def update(
        self,
        active_contacts: int,
        recent_casualties: int,
        contested_objectives: int,
        events_count: int,
    ) -> PacingInfo:
        """Update intensity and possibly transition phase."""
        # Calculate intensity (0-1)
        self.intensity = min(
            1.0,
            (
                active_contacts * 0.15
                + recent_casualties * 0.1
                + contested_objectives * 0.2
                + events_count * 0.05
            ),
        )

        self.phase_ticks += 1
        old_phase = self.phase

        # Phase transitions
        if self.phase == PacingPhase.CALM:
            if self.intensity > self.thresholds["calm_to_buildup"]:
                self.phase = PacingPhase.BUILD_UP
                self.phase_ticks = 0

        elif self.phase == PacingPhase.BUILD_UP:
            if self.intensity > self.thresholds["buildup_to_peak"]:
                self.phase = PacingPhase.PEAK
                self.phase_ticks = 0

        elif self.phase == PacingPhase.PEAK:
            if (
                self.intensity < self.thresholds["peak_to_relax"]
                or self.phase_ticks > self.peak_max_ticks
            ):
                self.phase = PacingPhase.RELAX
                self.phase_ticks = 0

        elif self.phase == PacingPhase.RELAX:
            if self.intensity < self.thresholds["relax_to_calm"]:
                self.phase = PacingPhase.CALM
                self.phase_ticks = 0

        if self.phase != old_phase:
            logger.info(
                "Pacing transition: %s -> %s (intensity=%.2f)",
                old_phase.value,
                self.phase.value,
                self.intensity,
            )

        return self.info

    def get_pacing_guidance(self) -> str:
        guidance = {
            PacingPhase.CALM: "Prepare defenses, optimize positions. No immediate threat.",
            PacingPhase.BUILD_UP: (
                "Enemy approaching. Increase readiness, prepare ambushes, stage reserves."
            ),
            PacingPhase.PEAK: (
                "Active combat. Commit reserves if needed, execute tactical maneuvers."
            ),
            PacingPhase.RELAX: "Combat winding down. Consolidate, reposition survivors, resupply.",
        }
        return guidance.get(self.phase, "Maintain current posture.")
