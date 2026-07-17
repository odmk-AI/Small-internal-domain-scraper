from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

from .checkpoint import load_checkpoint, save_checkpoint
from .config import load_site_config
from .excel_io import read_person_keys, write_output_csv, write_output_xlsx
from .models import ScrapeResult
from .scraper import safe_scrape_one, safe_scrape_taskboard


def normalise_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return cleaned.strip(".-_") or "Output"


def add_date_and_nick(path: Path, output_nick: str, run_date: date | None = None) -> Path:
    current_date = run_date or date.today()
    nick = normalise_filename_part(output_nick)
    stem = normalise_filename_part(path.stem)
    suffix = path.suffix or ".xlsx"
    return path.with_name(f"{stem}_{current_date.isoformat()}-{nick}{suffix}")


def resolve_local_output_path(requested_path: Path, output_dir: Path, output_nick: str) -> Path:
    local_output_dir = output_dir.resolve()
    if str(local_output_dir).startswith("\\"):
        raise ValueError("Output directory must be a local path, not a network/UNC path.")
    local_output_dir.mkdir(parents=True, exist_ok=True)

    dated_path = add_date_and_nick(requested_path, output_nick)

    if dated_path.is_absolute():
        candidate = dated_path.resolve()
    else:
        candidate = (local_output_dir / dated_path).resolve()

    try:
        candidate.relative_to(local_output_dir)
    except ValueError as exc:
        raise ValueError(
            f"Output paths must stay inside the local output directory: {local_output_dir}"
        ) from exc

    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "sites" / "wesser.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local configurable scraper for internal domain field extraction."
    )
    parser.add_argument("--input", required=False, type=Path, help="Input XLSX path. Required for person_search mode.")
    parser.add_argument("--output", required=True, type=Path, help="Output XLSX or CSV path.")
    parser.add_argument("--config", default=default_config_path(), type=Path, help="Site config JSON path.")
    parser.add_argument(
        "--output-dir",
        default="local_outputs",
        type=Path,
        help="Local-only directory for outputs and checkpoints.",
    )
    parser.add_argument("--sheet", default=None, help="Optional input worksheet name.")
    parser.add_argument(
        "--profile-dir",
        default=".edge-browser-profile",
        type=Path,
        help="Local browser profile directory. Sign in there on first run.",
    )
    parser.add_argument(
        "--browser-channel",
        default="msedge",
        help="Playwright browser channel. Defaults to Microsoft Edge (msedge).",
    )
    parser.add_argument("--timeout-ms", default=15000, type=int)
    parser.add_argument("--headless", action="store_true", help="Use only after a valid login exists in the profile.")
    parser.add_argument("--csv", default=None, type=Path, help="Optional extra CSV output path.")
    parser.add_argument("--years", default=None, help="Optional comma-separated year filter for taskboard mode, for example 2024,2025.")
    return parser


def _parse_year_filter(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _filtered_taskboard_urls(urls: tuple[str, ...], selected_years: set[str]) -> list[str]:
    if not selected_years:
        return list(urls)
    from .config import parse_year_from_text

    return [url for url in urls if parse_year_from_text(url) in selected_years]


def main() -> int:
    args = build_parser().parse_args()
    config = load_site_config(args.config.resolve())
    if config.mode not in {"person_search", "taskboard"}:
        print(f"Unsupported mode: {config.mode}", file=sys.stderr)
        return 2

    if config.mode == "person_search" and not args.input:
        print("--input is required for person_search mode.", file=sys.stderr)
        return 2

    try:
        output_path = resolve_local_output_path(args.output, args.output_dir, config.output_nick)
        csv_path = resolve_local_output_path(args.csv, args.output_dir, config.output_nick) if args.csv else None
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    checkpoint_path = output_path.with_suffix(".checkpoint.json")

    id_header = "Task ID" if config.mode == "taskboard" else config.id_headers[0]
    person_keys: list[str] = []
    existing: dict[str, ScrapeResult] = {}
    results: list[ScrapeResult] = []

    if config.mode == "person_search":
        input_xlsx = args.input.resolve()
        id_header, person_keys = read_person_keys(input_xlsx, args.sheet, config)
        if not person_keys:
            print("No valid IDs found.", file=sys.stderr)
            return 2
        existing = load_checkpoint(checkpoint_path, config)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(args.profile_dir.resolve()),
            channel=args.browser_channel,
            headless=args.headless,
            viewport={"width": 1400, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(config.base_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
        if "login" in page.url.lower() or "signin" in page.url.lower():
            print(f"Please sign in to {config.site_name} in the opened browser.")
            input("Press Enter here after the search page is visible...")

        if config.mode == "taskboard":
            selected_years = _parse_year_filter(args.years)
            taskboard_urls = _filtered_taskboard_urls(config.taskboard_urls, selected_years)
            if not taskboard_urls:
                print("No taskboard URLs match the requested year filter.", file=sys.stderr)
                context.close()
                return 2
            for url_index, taskboard_url in enumerate(taskboard_urls, start=1):
                if url_index > 1 or page.url != taskboard_url:
                    page.goto(taskboard_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                board_results = safe_scrape_taskboard(page, config, args.timeout_ms, taskboard_url)
                results.extend(board_results)
                print(f"{url_index}/{len(taskboard_urls)} taskboards processed. {len(board_results)} tasks found.")
        else:
            for index, person_key in enumerate(person_keys, start=1):
                if person_key in existing and existing[person_key].status in {"ok", "blank"}:
                    result = existing[person_key]
                else:
                    result = safe_scrape_one(page, config, person_key, args.timeout_ms)

                results.append(result)
                save_checkpoint(checkpoint_path, config, results)

                if index % 10 == 0 or index == len(person_keys):
                    counts = {
                        field.output_header: sum(1 for item in results if item.values.get(field.key) is not None)
                        for field in config.fields
                    }
                    counts_text = ", ".join(f"{name}: {count}" for name, count in counts.items())
                    print(f"{index}/{len(person_keys)} processed. Found values: {counts_text}.")

        context.close()

    if output_path.suffix.casefold() == ".csv":
        write_output_csv(output_path, id_header, config, results)
    else:
        write_output_xlsx(output_path, id_header, config, results)

    if csv_path:
        write_output_csv(csv_path, id_header, config, results)

    print(f"Done: {len(results)} IDs.")
    print(f"Output: {output_path}")
    if config.mode == "person_search":
        print(f"Checkpoint: {checkpoint_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
