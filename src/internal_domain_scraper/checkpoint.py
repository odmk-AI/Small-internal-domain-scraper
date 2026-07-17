from __future__ import annotations

import json
from pathlib import Path

from .config import SiteConfig
from .models import ScrapeResult


CHECKPOINT_VERSION = 3


def save_checkpoint(path: Path, config: SiteConfig, results: list[ScrapeResult]) -> None:
    payload = {
        "version": CHECKPOINT_VERSION,
        "site_name": config.site_name,
        "field_keys": [field.key for field in config.fields],
        "results": [
            {
                "person_key": result.person_key,
                "values": result.values,
                "status": result.status,
            }
            for result in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_checkpoint(path: Path, config: SiteConfig) -> dict[str, ScrapeResult]:
    if not path.exists():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_field_keys = [field.key for field in config.fields]
    if (
        payload.get("version") != CHECKPOINT_VERSION
        or payload.get("site_name") != config.site_name
        or payload.get("field_keys") != expected_field_keys
    ):
        return {}

    results: dict[str, ScrapeResult] = {}
    for item in payload.get("results", []):
        person_key = str(item["person_key"])
        results[person_key] = ScrapeResult(
            person_key=person_key,
            values=dict(item.get("values") or {}),
            status=str(item.get("status") or "unknown"),
        )
    return results
