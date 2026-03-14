from __future__ import annotations

import json
from pathlib import Path

from compliance_platform.service import build_default_service


def main() -> None:
    service = build_default_service(Path(__file__).resolve().parents[1] / "data")
    created = service.seed_default_modules()
    payload = {
        "seeded_count": len(created),
        "modules": service.list_modules(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

