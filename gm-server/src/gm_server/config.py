from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:14b"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout_seconds: float = 30.0


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080


class GameConfig(BaseSettings):
    tick_interval_seconds: float = 15.0
    anti_thrash_ticks: int = 3
    max_events_buffer: int = 50
    max_tick_history: int = 20


class PacingConfig(BaseSettings):
    calm_to_buildup: float = 0.3
    buildup_to_peak: float = 0.7
    peak_to_relax: float = 0.4
    relax_to_calm: float = 0.2
    peak_max_ticks: int = 8


class Config(BaseSettings):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    pacing: PacingConfig = Field(default_factory=PacingConfig)
    maps_dir: str = "shared/maps"
    prompts_dir: str = "gm-server/src/gm_server/prompts"


def load_config(path: Path | None = None) -> Config:
    """Load configuration from a YAML file, falling back to defaults."""
    if path is None:
        path = Path("gm-server/config.yaml")
    if not path.exists():
        return Config()
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return Config(
        llm=LLMConfig(**raw.get("llm", {})),
        server=ServerConfig(**raw.get("server", {})),
        game=GameConfig(**raw.get("game", {})),
        pacing=PacingConfig(**raw.get("pacing", {})),
        maps_dir=raw.get("maps_dir", "shared/maps"),
        prompts_dir=raw.get("prompts_dir", "gm-server/src/gm_server/prompts"),
    )
