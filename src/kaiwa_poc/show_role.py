from __future__ import annotations

from dotenv import load_dotenv

from .config import AppSettings
from .scenario_catalog import ScenarioCatalog


def main() -> None:
    load_dotenv(override=False)
    settings = AppSettings.from_env()
    catalog = ScenarioCatalog.load()
    scenario = catalog.get(settings.scenario_id)
    print(scenario.public_role_card())
    print("\nScenario có sẵn:")
    for item in catalog.list():
        selected = " *" if item.scenario_id == scenario.scenario_id else ""
        print(f"- {item.scenario_id}: {item.title_vi} ({item.level}){selected}")


if __name__ == "__main__":
    main()

