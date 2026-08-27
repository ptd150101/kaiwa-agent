from __future__ import annotations

import json

from dotenv import load_dotenv

from .config import AppSettings
from .repository import SessionRepository


def main() -> None:
    load_dotenv(override=False)
    settings = AppSettings.from_env()
    result = SessionRepository(settings.db_path).latest_report(settings.user_id)
    if result is None:
        print("Chưa có báo cáo nào cho user này.")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

