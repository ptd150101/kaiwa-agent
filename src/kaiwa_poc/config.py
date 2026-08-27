from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    soniox_api_key: str
    soniox_stt_model: str
    soniox_tts_model: str
    soniox_tts_voice: str
    soniox_tts_speed: float
    llm_api_key: str
    llm_base_url: str | None
    llm_model: str
    llm_temperature: float
    user_id: str
    scenario_id: str
    level: str
    feedback_mode: str
    db_path: Path
    coach_mode: str
    metrics_enabled: bool

    @classmethod
    def from_env(cls) -> AppSettings:
        base_url = os.getenv("LLM_BASE_URL", "").strip() or None
        return cls(
            soniox_api_key=os.getenv("SONIOX_API_KEY", "").strip(),
            soniox_stt_model=os.getenv("SONIOX_STT_MODEL", "stt-rt-v5").strip(),
            soniox_tts_model=os.getenv("SONIOX_TTS_MODEL", "tts-rt-v2").strip(),
            soniox_tts_voice=os.getenv("SONIOX_TTS_VOICE", "Maya").strip(),
            soniox_tts_speed=float(os.getenv("SONIOX_TTS_SPEED", "0.92")),
            llm_api_key=(
                os.getenv("LLM_API_KEY", "").strip()
                or os.getenv("OPENAI_API_KEY", "").strip()
            ),
            llm_base_url=base_url,
            llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini").strip(),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.45")),
            user_id=os.getenv("KAIWA_USER_ID", "demo-user").strip(),
            scenario_id=os.getenv(
                "KAIWA_SCENARIO_ID", "lunch_with_colleague_n4"
            ).strip(),
            level=os.getenv("KAIWA_LEVEL", "N4").strip().upper(),
            feedback_mode=os.getenv("KAIWA_FEEDBACK_MODE", "delayed").strip(),
            db_path=Path(os.getenv("KAIWA_DB_PATH", "var/kaiwa.db")),
            coach_mode=os.getenv("KAIWA_COACH_MODE", "llm").strip().lower(),
            metrics_enabled=_env_bool("KAIWA_METRICS_ENABLED", True),
        )

    def validate_voice_runtime(self) -> None:
        missing: list[str] = []
        if not self.soniox_api_key or self.soniox_api_key == "replace-me":
            missing.append("SONIOX_API_KEY")
        if not self.llm_api_key or self.llm_api_key == "replace-me":
            missing.append("LLM_API_KEY")
        if missing:
            raise ConfigurationError(
                "Missing required configuration: " + ", ".join(missing)
            )
        if not 0.7 <= self.soniox_tts_speed <= 1.3:
            raise ConfigurationError("SONIOX_TTS_SPEED must be between 0.7 and 1.3")
        if self.feedback_mode != "delayed":
            raise ConfigurationError("PoC v0.1 supports only KAIWA_FEEDBACK_MODE=delayed")
        if self.coach_mode not in {"llm", "rules"}:
            raise ConfigurationError("KAIWA_COACH_MODE must be llm or rules")
