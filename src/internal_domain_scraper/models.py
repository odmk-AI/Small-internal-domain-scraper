from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScrapeResult:
    person_key: str
    values: dict[str, float | str | None]
    status: str
