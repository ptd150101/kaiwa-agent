from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RoleSpec:
    identity: str
    relationship: str
    personality: str = ""
    goals: tuple[str, ...] = ()
    known_information: tuple[str, ...] = ()
    hidden_information: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> RoleSpec:
        return cls(
            identity=str(value["identity"]),
            relationship=str(value["relationship"]),
            personality=str(value.get("personality", "")),
            goals=tuple(value.get("goals", [])),
            known_information=tuple(value.get("known_information", [])),
            hidden_information=tuple(value.get("hidden_information", [])),
        )


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    title_vi: str
    level: str
    setting: str
    user_role: RoleSpec
    ai_role: RoleSpec
    language_targets: tuple[str, ...]
    hidden_events: tuple[str, ...]
    success_conditions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ScenarioSpec:
        return cls(
            scenario_id=str(value["scenario_id"]),
            title_vi=str(value["title_vi"]),
            level=str(value["level"]),
            setting=str(value["setting"]),
            user_role=RoleSpec.from_mapping(value["user_role"]),
            ai_role=RoleSpec.from_mapping(value["ai_role"]),
            language_targets=tuple(value.get("language_targets", [])),
            hidden_events=tuple(value.get("hidden_events", [])),
            success_conditions=tuple(value.get("success_conditions", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_role_card(self) -> str:
        goals = "\n".join(f"- {item}" for item in self.user_role.goals)
        known = "\n".join(f"- {item}" for item in self.user_role.known_information)
        targets = ", ".join(self.language_targets)
        known_block = f"\nThông tin bạn biết:\n{known}" if known else ""
        return (
            f"CHỦ ĐỀ: {self.title_vi} ({self.level})\n"
            f"BỐI CẢNH: {self.setting}\n"
            f"VAI CỦA BẠN: {self.user_role.identity}\n"
            f"QUAN HỆ: {self.user_role.relationship}\n"
            f"NHIỆM VỤ:\n{goals}"
            f"{known_block}\n"
            f"MẪU CÂU NÊN LUYỆN: {targets}"
        )


@dataclass(frozen=True)
class Turn:
    role: Literal["user", "assistant"]
    text: str
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class SessionRuntime:
    session_id: str
    user_id: str
    scenario: ScenarioSpec
    feedback_mode: str
    started_at: str
    turns: list[Turn] = field(default_factory=list)
    ended_at: str | None = None
    finalized: bool = False

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        scenario: ScenarioSpec,
        feedback_mode: str,
    ) -> SessionRuntime:
        return cls(
            session_id=str(uuid4()),
            user_id=user_id,
            scenario=scenario,
            feedback_mode=feedback_mode,
            started_at=utc_now_iso(),
        )

    def add_turn(self, role: Literal["user", "assistant"], text: str) -> None:
        normalized = " ".join(text.split()).strip()
        if not normalized:
            return
        if self.turns and self.turns[-1].role == role and self.turns[-1].text == normalized:
            return
        self.turns.append(Turn(role=role, text=normalized))

    def finish(self) -> None:
        if self.ended_at is None:
            self.ended_at = utc_now_iso()
        self.finalized = True

    def transcript(self) -> list[dict[str, str]]:
        return [asdict(turn) for turn in self.turns]


@dataclass
class LearnerProfile:
    user_id: str
    level: str = "N4"
    completed_sessions: int = 0
    recurring_issues: dict[str, int] = field(default_factory=dict)
    last_scenario_id: str | None = None
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

