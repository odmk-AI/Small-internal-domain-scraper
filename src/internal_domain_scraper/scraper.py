from __future__ import annotations

import re
import time
from urllib.parse import unquote
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .config import FieldConfig, SiteConfig, parse_year_from_text
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
    if not config.search:
        raise ValueError("Config mode requires search settings.")

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
    if not config.search:
        raise ValueError("Config mode requires search settings.")
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


def scrape_taskboard(page: Any, config: SiteConfig, timeout_ms: int, source_url: str | None = None) -> list[ScrapeResult]:
    page.locator(".wit-card.taskboard-card").first.wait_for(state="visible", timeout=timeout_ms)
    _collapse_then_expand_all(page, timeout_ms)
    page.locator(".wit-card.taskboard-card").first.wait_for(state="visible", timeout=timeout_ms)
    sprint = _sprint_from_url(source_url or page.url) or _sprint_from_page(page)
    year = parse_year_from_text(sprint) or parse_year_from_text(source_url or page.url)

    rows = page.locator("tr.full-height")
    results: list[ScrapeResult] = []
    seen_task_ids: set[str] = set()

    for row_index in range(rows.count()):
        row = rows.nth(row_index)
        parent_card = row.locator("td.taskboard-parent-cell .wit-card.taskboard-card").first
        parent_id = ""
        parent_title = ""
        if parent_card.count():
            parent_id = _attribute(parent_card, "data-itemid") or _first_text(parent_card, ".selectable-text")
            parent_title = _first_text(parent_card, ".title-text")

        columns = row.locator("td.taskboard-expanded-cell[data-columnname]")
        for column_index in range(columns.count()):
            column = columns.nth(column_index)
            board_column = _attribute(column, "data-columnname") or ""
            cards = column.locator('.wit-card.taskboard-card[aria-label^="Task,"]')
            for card_index in range(cards.count()):
                card = cards.nth(card_index)
                task_id = _attribute(card, "data-itemid") or _first_text(card, ".selectable-text")
                if not task_id or task_id in seen_task_ids:
                    continue
                seen_task_ids.add(task_id)

                values = {
                    "year": year,
                    "sprint": sprint,
                    "parent_issue_id": parent_id,
                    "parent_issue_title": parent_title,
                    "task_title": _first_text(card, ".title-text"),
                    "board_column": board_column,
                    "task_state": _first_text(card, ".work-item-state-name span"),
                    "assigned_to": _first_text(card, ".card-assigned-to .identity-display-name span"),
                    "original_estimate": _field_value(card, "Original Estimate"),
                    "remaining_work": _remaining_work(card),
                    "completed_work": _field_value(card, "Completed Work"),
                }
                results.append(ScrapeResult(person_key=task_id, values=values, status="ok"))

    return results


def safe_scrape_taskboard(
    page: Any, config: SiteConfig, timeout_ms: int, source_url: str | None = None
) -> list[ScrapeResult]:
    try:
        return scrape_taskboard(page, config, timeout_ms, source_url)
    except PlaywrightTimeoutError:
        return []


def _sprint_from_url(url: str) -> str:
    decoded = unquote(url)
    match = re.search(r"Sprint[ /%]*(20\d{2}[-_ ]?\d{1,2})", decoded)
    if match:
        value = match.group(1).replace("_", "-").replace(" ", "-")
        return f"Sprint {value}"
    return ""


def _sprint_from_page(page: Any) -> str:
    labels = page.locator(".bolt-dropdown-expandable-button-label")
    for index in range(labels.count()):
        try:
            text = labels.nth(index).inner_text(timeout=1000).strip()
        except Exception:
            continue
        match = re.search(r"Sprint\s+20\d{2}[-_ ]?\d{1,2}", text)
        if match:
            return match.group(0).replace("_", "-")
    return ""


def _collapse_then_expand_all(page: Any, timeout_ms: int) -> None:
    _click_button_text(page, "Collapse all", timeout_ms)
    page.wait_for_timeout(250)
    _click_button_text(page, "Expand all", timeout_ms)
    page.wait_for_timeout(500)


def _click_button_text(page: Any, text: str, timeout_ms: int) -> bool:
    click_timeout = min(timeout_ms, 3000)
    candidates = [
        page.get_by_role("button", name=text),
        page.locator("button").filter(has_text=text),
    ]
    for locator in candidates:
        try:
            if locator.count() == 0:
                continue
            button = locator.first
            button.wait_for(state="visible", timeout=1000)
            button.click(timeout=click_timeout)
            return True
        except Exception:
            continue
    return False


def _first_text(scope: Any, selector: str) -> str:
    locator = scope.locator(selector)
    if locator.count() == 0:
        return ""
    try:
        return locator.first.inner_text(timeout=1000).strip()
    except Exception:
        return ""


def _attribute(scope: Any, name: str) -> str:
    try:
        return str(scope.get_attribute(name, timeout=1000) or "").strip()
    except Exception:
        return ""


def _field_value(card: Any, label: str) -> str:
    containers = card.locator(".field-container")
    for index in range(containers.count()):
        container = containers.nth(index)
        if _first_text(container, ".label") == label:
            return _first_text(container, ".value .text-ellipsis")
    return ""


def _remaining_work(card: Any) -> str:
    return _first_text(card, ".remaining-work .text-ellipsis")
