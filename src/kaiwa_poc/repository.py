from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .domain import LearnerProfile, SessionRuntime, utc_now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    scenario_json TEXT NOT NULL,
    feedback_mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (session_id, turn_index),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS reports (
    session_id TEXT PRIMARY KEY,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS learner_profiles (
    user_id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    completed_sessions INTEGER NOT NULL,
    recurring_issues_json TEXT NOT NULL,
    last_scenario_id TEXT,
    updated_at TEXT NOT NULL
);
"""


class SessionRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def save_session(self, session: SessionRuntime) -> None:
        status = "completed" if session.finalized else "active"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, user_id, scenario_id, scenario_json, feedback_mode,
                    started_at, ended_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    ended_at = excluded.ended_at,
                    status = excluded.status
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.scenario.scenario_id,
                    json.dumps(session.scenario.to_dict(), ensure_ascii=False),
                    session.feedback_mode,
                    session.started_at,
                    session.ended_at,
                    status,
                ),
            )
            connection.executemany(
                """
                INSERT INTO turns (session_id, turn_index, role, text, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id, turn_index) DO UPDATE SET
                    role = excluded.role,
                    text = excluded.text,
                    timestamp = excluded.timestamp
                """,
                [
                    (session.session_id, index, turn.role, turn.text, turn.timestamp)
                    for index, turn in enumerate(session.turns)
                ],
            )

    def get_profile(self, user_id: str, default_level: str = "N4") -> LearnerProfile:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM learner_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return LearnerProfile(user_id=user_id, level=default_level)
        return LearnerProfile(
            user_id=row["user_id"],
            level=row["level"],
            completed_sessions=row["completed_sessions"],
            recurring_issues=json.loads(row["recurring_issues_json"]),
            last_scenario_id=row["last_scenario_id"],
            updated_at=row["updated_at"],
        )

    def save_report_and_update_profile(
        self,
        session: SessionRuntime,
        report: dict[str, Any],
    ) -> LearnerProfile:
        profile = self.get_profile(session.user_id, session.scenario.level)
        issues = dict(profile.recurring_issues)
        for correction in report.get("corrections", []):
            category = str(correction.get("category", "other"))
            issues[category] = issues.get(category, 0) + 1
        updated = LearnerProfile(
            user_id=profile.user_id,
            level=profile.level,
            completed_sessions=profile.completed_sessions + 1,
            recurring_issues=issues,
            last_scenario_id=session.scenario.scenario_id,
            updated_at=utc_now_iso(),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (session_id, report_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    report_json = excluded.report_json,
                    created_at = excluded.created_at
                """,
                (
                    session.session_id,
                    json.dumps(report, ensure_ascii=False),
                    utc_now_iso(),
                ),
            )
            connection.execute(
                """
                INSERT INTO learner_profiles (
                    user_id, level, completed_sessions, recurring_issues_json,
                    last_scenario_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    level = excluded.level,
                    completed_sessions = excluded.completed_sessions,
                    recurring_issues_json = excluded.recurring_issues_json,
                    last_scenario_id = excluded.last_scenario_id,
                    updated_at = excluded.updated_at
                """,
                (
                    updated.user_id,
                    updated.level,
                    updated.completed_sessions,
                    json.dumps(updated.recurring_issues, ensure_ascii=False),
                    updated.last_scenario_id,
                    updated.updated_at,
                ),
            )
        return updated

    def latest_report(self, user_id: str | None = None) -> dict[str, Any] | None:
        query = """
            SELECT s.session_id, s.user_id, s.scenario_id, s.started_at, s.ended_at,
                   r.report_json, r.created_at
            FROM reports r
            JOIN sessions s ON s.session_id = r.session_id
        """
        params: tuple[Any, ...] = ()
        if user_id:
            query += " WHERE s.user_id = ?"
            params = (user_id,)
        query += " ORDER BY r.created_at DESC LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "scenario_id": row["scenario_id"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "created_at": row["created_at"],
            "report": json.loads(row["report_json"]),
        }

