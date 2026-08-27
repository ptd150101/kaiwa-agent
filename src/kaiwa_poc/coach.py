from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .config import AppSettings
from .domain import SessionRuntime
from .prompts import build_coach_prompt


class Coach(Protocol):
    async def assess(self, session: SessionRuntime) -> dict[str, Any]: ...


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("Coach response must be a JSON object")
    return value


def _validate_report(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "summary_vi",
        "strengths",
        "corrections",
        "task_completion",
        "scores",
        "next_drill",
        "limitations",
    }
    missing = required.difference(value)
    if missing:
        raise ValueError("Coach report is missing fields: " + ", ".join(sorted(missing)))
    if not isinstance(value["corrections"], list):
        raise ValueError("Coach report corrections must be a list")
    if not isinstance(value["scores"], dict):
        raise ValueError("Coach report scores must be an object")
    for key in ("grammar", "vocabulary", "politeness", "naturalness", "task_completion"):
        score = value["scores"].get(key)
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f"Coach score '{key}' must be numeric")
        value["scores"][key] = max(0, min(100, round(score)))
    return value


class LLMLanguageCoach:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def assess(self, session: SessionRuntime) -> dict[str, Any]:
        from openai import AsyncOpenAI, BadRequestError

        kwargs: dict[str, Any] = {"api_key": self._settings.llm_api_key}
        if self._settings.llm_base_url:
            kwargs["base_url"] = self._settings.llm_base_url
        client = AsyncOpenAI(**kwargs)
        request: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": [{"role": "user", "content": build_coach_prompt(session)}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await client.chat.completions.create(**request)
        except BadRequestError:
            # Some local OpenAI-compatible servers do not implement response_format.
            request.pop("response_format", None)
            response = await client.chat.completions.create(**request)
        content = response.choices[0].message.content or "{}"
        return _validate_report(_extract_json(content))


class RuleBasedCoach:
    """Safe fallback for smoke tests; it deliberately avoids pretending to be a full grader."""

    async def assess(self, session: SessionRuntime) -> dict[str, Any]:
        user_text = "\n".join(turn.text for turn in session.turns if turn.role == "user")
        corrections: list[dict[str, Any]] = []
        if "昨日" in user_text and "行きません。" in user_text:
            corrections.append(
                {
                    "original": "昨日、会社へ行きません。",
                    "corrected": "昨日、会社へ行きませんでした。",
                    "more_natural": "昨日は会社へ行きませんでした。",
                    "category": "grammar",
                    "explanation_vi": "Sự việc xảy ra hôm qua nên dùng thể phủ định quá khứ.",
                    "confidence": 0.9,
                }
            )
        return {
            "summary_vi": (
                "Đã lưu transcript PoC. Hãy bật KAIWA_COACH_MODE=llm "
                "để có đánh giá ngữ cảnh đầy đủ."
            ),
            "strengths": ["Đã tham gia hội thoại và tạo dữ liệu để đánh giá."],
            "corrections": corrections,
            "task_completion": {
                "completed": [],
                "missing": list(session.scenario.success_conditions),
            },
            "scores": {
                "grammar": None,
                "vocabulary": None,
                "politeness": None,
                "naturalness": None,
                "task_completion": None,
            },
            "next_drill": {
                "instruction_vi": "Lặp lại một câu mục tiêu rồi chạy Coach bằng LLM.",
                "example_ja": session.scenario.language_targets[0],
            },
            "limitations": [
                "Rule mode không phải bộ chấm ngôn ngữ.",
                "Chưa có acoustic metrics nên không chấm phát âm.",
            ],
        }


def create_coach(settings: AppSettings) -> Coach:
    if settings.coach_mode == "rules":
        return RuleBasedCoach()
    return LLMLanguageCoach(settings)
