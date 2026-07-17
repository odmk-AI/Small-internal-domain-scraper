from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    base_url: str
    id_headers: tuple[str, ...]
    search: SearchConfig
    fields: tuple[FieldConfig, ...]


def load_site_config(path: Path) -> SiteConfig:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    search_payload = payload["search"]
    return SiteConfig(
        site_name=str(payload["site_name"]),
        base_url=str(payload["base_url"]),
        id_headers=tuple(str(item) for item in payload["id_headers"]),
        search=SearchConfig(
            open_shortcut=str(search_payload["open_shortcut"]),
            input_selector=str(search_payload["input_selector"]),
            submit_selector=str(search_payload["submit_selector"]),
            loaded_markers=tuple(str(item) for item in search_payload["loaded_markers"]),
        ),
        fields=tuple(
            FieldConfig(
                key=str(item["key"]),
                label=str(item["label"]),
                output_header=str(item["output_header"]),
                type=str(item.get("type", "text")),
            )
            for item in payload["fields"]
        ),
    )
