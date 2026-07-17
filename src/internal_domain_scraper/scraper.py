from __future__ import annotations

import re
import time
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .config import FieldConfig, SiteConfig
from .models import ScrapeResult


def parse_field_value(text: str, field: FieldConfig) -> tuple[float | str | None, str]:
    label_index = text.find(field.label)
    if label_index < 0:
        return None, "field_not_found"

    after_label = text[label_index + len(field.label) : label_index + len(field.label) + 180]
    lines = [line.strip() for line in after_label.splitlines() if line.strip()]
    if not lines:
        return None, "blank"

    first = lines[0].replace(",", ".")
    if field.type == "percent":
        if re.fullmatch(r"\d+(?:\.\d+)?", first):
            return float(first) / 100.0, "ok"
        return None, "blank"

    return lines[0], "ok"


def open_search(page: Any, config: SiteConfig, timeout_ms: int) -> None:
    search_input = page.locator(config.search.input_selector)
    try:
        if search_input.count() == 1 and search_input.is_visible():
            return
    except Exception:
        pass

    try:
        page.locator("body").press(config.search.open_shortcut, timeout=timeout_ms)
        search_input.wait_for(state="visible", timeout=timeout_ms)
        return
    except Exception:
        page.goto(config.base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        search_input.wait_for(state="visible", timeout=timeout_ms)


def scrape_one(page: Any, config: SiteConfig, person_key: str, timeout_ms: int) -> ScrapeResult:
    open_search(page, config, timeout_ms)

    page.locator(config.search.input_selector).fill(person_key)
    page.locator(config.search.submit_selector).click(timeout=timeout_ms)

    deadline = time.time() + (timeout_ms / 1000)
    last_values: dict[str, float | str | None] = {field.key: None for field in config.fields}
    last_status = "field_not_found"

    while time.time() < deadline:
        text = page.locator("body").inner_text(timeout=timeout_ms)
        has_current_person = any(marker.format(id=person_key) in text for marker in config.search.loaded_markers)
        values: dict[str, float | str | None] = {}
        statuses: dict[str, str] = {}

        for field in config.fields:
            value, status = parse_field_value(text, field)
            values[field.key] = value
            statuses[field.key] = status

        fields_ready = all(status in {"ok", "blank"} for status in statuses.values())
        if fields_ready and has_current_person:
            row_status = "ok" if any(value is not None for value in values.values()) else "blank"
            return ScrapeResult(person_key=person_key, values=values, status=row_status)

        last_values = values
        last_status = "_".join(f"{key}_{value}" for key, value in statuses.items())
        page.wait_for_timeout(250)

    return ScrapeResult(person_key=person_key, values=last_values, status=f"timeout_{last_status}")


def safe_scrape_one(page: Any, config: SiteConfig, person_key: str, timeout_ms: int) -> ScrapeResult:
    try:
        return scrape_one(page, config, person_key, timeout_ms)
    except PlaywrightTimeoutError:
        return ScrapeResult(
            person_key=person_key,
            values={field.key: None for field in config.fields},
            status="timeout",
        )
