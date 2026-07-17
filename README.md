# Small Internal Domain Scraper

Small Internal Domain Scraper is a local, configurable browser scraper for extracting a small set of values from internal web applications into XLSX or CSV output.

The first supported site configuration is Wesser. It reads a local input Excel file containing pseudonymous IDs or fundraiser numbers, opens the corresponding record in the browser, extracts configured percent fields, and writes a minimal result file.

## Current Wesser Use Case

Input:

- Local `.xlsx`
- One ID column named `PseudoID` or `Fundraiser Number`

Output:

- The same ID column
- `Individuelle StRL%`
- `Individuelle Vorschuss%`

No names, addresses, email addresses, full profile text, HTML dumps, screenshots, or browser session data are intentionally written by the scraper.

Generated outputs and checkpoints are constrained to a dedicated local output directory. The default is `local_outputs/`, which is ignored by Git and should remain local to the operator's machine.

Output filenames automatically include the run date and configured project nick, for example `Ausgabe_Werte_2026-07-17-WesserPortal.xlsx`. Current nicks are `WesserPortal` for Wesser Portal and `CEATimetracking` for the planned CEA Timetracking configuration.

## Repository Layout

```text
.
├── config/
│   └── sites/
│       └── wesser.json          # Site URL, selectors, record markers, fields
├── src/
│   └── internal_domain_scraper/
│       ├── checkpoint.py        # Resume file handling
│       ├── cli.py               # Command line entrypoint
│       ├── config.py            # JSON config models/loaders
│       ├── excel_io.py          # Input/output spreadsheet and CSV handling
│       ├── models.py            # Shared result dataclass
│       └── scraper.py           # Playwright navigation and parsing logic
├── .gitignore                   # Blocks local data, browser profiles, outputs
├── pyproject.toml               # Package metadata and console script
├── requirements.txt             # Editable local install
└── wesser_strl_scraper.py        # Backwards-compatible entrypoint
```

## Installation

Run from the project directory:

```powershell
cd "D:\Codex\Small Scraper"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell blocks activation, use the virtual environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

## Run

XLSX output:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --input ".\Liste 2026-07-16.xlsx" `
  --output "Ausgabe_Werte.xlsx"
```

CSV output:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --input ".\Liste 2026-07-16.xlsx" `
  --output "Ausgabe_Werte.csv"
```

Using the installed console script:

```powershell
.\.venv\Scripts\internal-domain-scraper.exe `
  --config ".\config\sites\wesser.json" `
  --input ".\Liste 2026-07-16.xlsx" `
  --output "Ausgabe_Werte.xlsx"
```

On first run, a local Chromium browser window opens. Sign in to the internal site in that browser. If the script prompts you, press Enter after the search page is visible.

## Command Line Options

```text
--input        Required for person_search mode. Not used for taskboard mode.
--output       Required. Output XLSX or CSV path.
--output-dir   Optional. Local output directory. Defaults to local_outputs.
--config       Optional. Site config JSON path. Defaults to config/sites/wesser.json.
--sheet        Optional. Input worksheet name. Defaults to first worksheet.
--profile-dir  Optional. Local browser profile directory. Defaults to .browser-profile.
--timeout-ms   Optional. Per-record timeout in milliseconds. Defaults to 15000.
--headless     Optional. Run browser without UI after a valid login exists.
--csv          Optional. Write an additional CSV output.
```


### Local Output Directory Rules

`--output` and `--csv` are constrained to the configured local output directory:

- Bare filenames such as `Ausgabe_Werte.xlsx` are written to `local_outputs/Ausgabe_Werte_YYYY-MM-DD-Nick.xlsx`.
- Relative paths such as `monthly/Ausgabe_Werte.xlsx` are written under `local_outputs/monthly/` with the same date-and-nick suffix.
- Absolute paths or `..` traversal outside the output directory are rejected.
- Checkpoints are written beside the output file inside the same local output directory.

## Site Configuration

Site-specific behavior lives in JSON, not in the core scraper code.

Example: `config/sites/wesser.json`

```json
{
  "site_name": "Wesser",
  "base_url": "https://my.wesser.de/FundraiserList",
  "id_headers": ["PseudoID", "Fundraiser Number"],
  "search": {
    "open_shortcut": "Control+M",
    "input_selector": "input[placeholder^=\"Fundraiser\"]",
    "submit_selector": "button.btn-primary",
    "loaded_markers": ["F# {id}", "Ma-Nummer\n{id}"]
  },
  "fields": [
    {
      "key": "st_rl_percent",
      "label": "Individuelle StRL%",
      "output_header": "Individuelle StRL%",
      "type": "percent"
    }
  ]
}
```

### Configuration Fields

`site_name`  
Human-readable site identifier. Also used to validate checkpoints.

`mode`
Scraper mode. Use `person_search` for input-list based record lookup or `taskboard` for visible Azure DevOps sprint board extraction.

`output_nick`
Short project nick appended to generated output and checkpoint filenames, for example `WesserPortal` or `CEATimetracking`.

`base_url`  
Search page URL used as fallback if the keyboard shortcut does not open the search screen.

`id_headers`  
Accepted input Excel header names. The first matching header is used as the ID column.

`search.open_shortcut`  
Keyboard shortcut that opens the search view from a detail page, for example `Control+M`.

`search.input_selector`  
CSS selector for the search input.

`search.submit_selector`  
CSS selector for the search/submit button.

`search.loaded_markers`  
Text markers used to confirm that the requested record is loaded. Use `{id}` as placeholder.

`fields`  
List of values to extract. Each field has:

- `key`: stable internal key used in checkpoints
- `label`: exact visible label to parse after
- `output_header`: column header in output files
- `type`: currently `percent` or `text`

## Adding Or Changing Fields

To add a new percent field, edit `config/sites/wesser.json`:

```json
{
  "key": "new_percent_field",
  "label": "Visible Label %",
  "output_header": "Visible Label %",
  "type": "percent"
}
```

No Python change is required if the field appears as a visible label followed by the value in the page text.

## Adding Another Site

1. Copy `config/sites/wesser.json` to a new file.
2. Change `base_url`, selectors, loaded markers, and field labels.
3. Run with `--config`.

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --config ".\config\sites\new-site.json" `
  --input ".\Input.xlsx" `
  --output "Output.xlsx"
```

If the new site needs a different navigation pattern, keep that change isolated in `src/internal_domain_scraper/scraper.py`.


## CEA Timetracking

CEA Timetracking uses `mode: "taskboard"`. It opens the configured Azure DevOps sprint taskboard and exports visible task cards. Unlike the Wesser mode, it does not require an input Excel file.

Example:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --config ".\config\sites\cea_timetracking.json" `
  --output "Tasks.xlsx"
```

The generated file is written below `local_outputs/` with date and nick, for example:

```text
local_outputs/Tasks_2026-07-17-CEATimetracking.xlsx
```

Current CEA output columns:

- Task ID
- Sprint
- Parent Issue ID
- Parent Issue Title
- Task Title
- Board Column
- Task State
- Assigned To
- Original Estimate
- Remaining Work
- Completed Work

`Assigned To` is personal data when real employees are assigned. Do not paste real taskboard HTML, names, emails, screenshots, outputs, or checkpoints into external tools.

To change the sprint, edit `base_url` in `config/sites/cea_timetracking.json` to the approved sprint taskboard URL.

## Checkpoints

The scraper writes a checkpoint beside the output file inside `local_outputs/`:

```text
local_outputs/Ausgabe_Werte.checkpoint.json
```

The checkpoint allows a run to resume if interrupted. It is ignored by Git and should be deleted after a successful run if no longer needed.

Checkpoint compatibility is guarded by:

- checkpoint version
- configured site name
- configured field keys

If the site config changes materially, old checkpoints are ignored.

## Git And Local Data

The repository intentionally ignores:

- `.venv/`
- `.browser-profile/`
- `.wesser-browser-profile/`
- `local_outputs/`
- `*.xlsx`
- `*.xls`
- `*.csv`
- `*.checkpoint.json`
- temporary Excel lock files such as `~$...`

Before committing, verify:

```powershell
git status --ignored
```

Only source code, docs, and config should be tracked.

## Troubleshooting

`ModuleNotFoundError: No module named 'openpyxl'`  
Install dependencies in the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Browser opens but is not signed in  
Sign in manually in the opened browser. The login is stored only in the local profile directory.

No IDs found  
Check that the input sheet has a header listed in `id_headers`, such as `PseudoID`.

Timeouts  
Increase `--timeout-ms`, verify the search selectors in the config, or run non-headless to observe the browser.

Wrong or empty values  
Check the field `label` in the site config. The parser expects the visible label followed by the value in the page text.

## Privacy Documentation

See [GDPR_PRIVACY_MEASURES.md](./GDPR_PRIVACY_MEASURES.md) for the project’s data protection design, restrictions, residual risks, and operational checklist.
