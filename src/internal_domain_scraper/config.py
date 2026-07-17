from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote


@dataclass(frozen=True)
class FieldConfig:
    key: str
    label: str
    output_header: str
    type: str = "text"


@dataclass(frozen=True)
class SearchConfig:
    open_shortcut: str
    input_selector: str
    submit_selector: str
    loaded_markers: tuple[str, ...]


@dataclass(frozen=True)
class SiteConfig:
    site_name: str
    output_nick: str
    base_url: str
    taskboard_urls: tuple[str, ...]
    id_headers: tuple[str, ...]
    search: SearchConfig | None
    fields: tuple[FieldConfig, ...]
    mode: str = "person_search"


def parse_year_from_text(value: str) -> str:
    decoded = unquote(value)
    match = re.search(r"(?:Sprint\s*)?(20\d{2})", decoded)
    return match.group(1) if match else ""


def load_site_config(path: Path) -> SiteConfig:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))
    search_payload = payload.get("search")
    search = None
    if search_payload:
        search = SearchConfig(
            open_shortcut=str(search_payload["open_shortcut"]),
            input_selector=str(search_payload["input_selector"]),
            submit_selector=str(search_payload["submit_selector"]),
            loaded_markers=tuple(str(item) for item in search_payload["loaded_markers"]),
        )

    return SiteConfig(
        site_name=str(payload["site_name"]),
        output_nick=str(payload.get("output_nick", payload["site_name"])),
        base_url=str(payload["base_url"]),
        taskboard_urls=tuple(str(item) for item in payload.get("taskboard_urls", [payload["base_url"]])),
        id_headers=tuple(str(item) for item in payload.get("id_headers", [])),
        search=search,
        fields=tuple(
            FieldConfig(
                key=str(item["key"]),
                label=str(item.get("label", item["key"])),
                output_header=str(item["output_header"]),
                type=str(item.get("type", "text")),
            )
            for item in payload["fields"]
        ),
        mode=str(payload.get("mode", "person_search")),
    )
