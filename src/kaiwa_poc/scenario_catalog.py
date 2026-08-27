from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from .domain import ScenarioSpec


class ScenarioNotFoundError(KeyError):
    pass


class ScenarioCatalog:
    def __init__(self, scenarios: list[ScenarioSpec]) -> None:
        self._scenarios = {scenario.scenario_id: scenario for scenario in scenarios}
        if not self._scenarios:
            raise ValueError("Scenario catalog cannot be empty")

    @classmethod
    def load(cls, path: str | Path | None = None) -> ScenarioCatalog:
        source = Path(path) if path else Path(str(files("kaiwa_poc").joinpath("scenarios.json")))
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls([ScenarioSpec.from_mapping(item) for item in payload["scenarios"]])

    def get(self, scenario_id: str) -> ScenarioSpec:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:
            choices = ", ".join(sorted(self._scenarios))
            raise ScenarioNotFoundError(
                f"Unknown scenario '{scenario_id}'. Available: {choices}"
            ) from exc

    def list(self) -> list[ScenarioSpec]:
        return list(self._scenarios.values())

