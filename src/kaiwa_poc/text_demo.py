from __future__ import annotations

import asyncio
import json

from .coach import RuleBasedCoach
from .domain import SessionRuntime
from .scenario_catalog import ScenarioCatalog


async def _run() -> None:
    scenario = ScenarioCatalog.load().get("lunch_with_colleague_n4")
    session = SessionRuntime.create(
        user_id="offline-demo",
        scenario=scenario,
        feedback_mode="delayed",
    )
    session.add_turn("assistant", "お疲れさまです。もうすぐ昼休みですね。")
    session.add_turn("user", "一緒に昼ご飯を食べませんか。")
    session.add_turn("assistant", "いいですね。何を食べたいですか。")
    session.add_turn("user", "昨日、会社へ行きません。今日はラーメンを食べたいです。")
    session.finish()
    report = await RuleBasedCoach().assess(session)
    print(scenario.public_role_card())
    print("\nTRANSCRIPT")
    print(json.dumps(session.transcript(), ensure_ascii=False, indent=2))
    print("\nREPORT (RULE-BASED SMOKE TEST ONLY)")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
