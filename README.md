# Small Internal Domain Scraper

Local configurable scraper for internal web pages. The first site config is for Wesser and extracts:

- `Individuelle StRL%`
- `Individuelle Vorschuss%`

The project is designed so future site, selector, or field changes live mostly in JSON config instead of Python code.

## Safety Model

- Run locally only.
- Do not commit input Excel files, output files, checkpoints, virtual environments, or browser profiles.
- `.gitignore` excludes local data files (`*.xlsx`, `*.csv`), checkpoints, and browser profiles.
- The scraper writes only the configured ID column and configured extracted fields.
- It does not intentionally store page HTML, screenshots, names, addresses, emails, or full profile text.

## Install

```powershell
cd "D:\Codex\Small Scraper"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell blocks activation, use the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

## Run

XLSX output:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --input ".\Liste 2026-07-16.xlsx" `
  --output ".\Ausgabe_Werte.xlsx"
```

CSV output:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --input ".\Liste 2026-07-16.xlsx" `
  --output ".\Ausgabe_Werte.csv"
```

On first run, a browser window opens. Sign in locally, then press Enter in the terminal if prompted.

## Configure A Site

Site configuration lives in:

```text
config/sites/wesser.json
```

Important sections:

- `base_url`: search page URL
- `id_headers`: accepted input Excel header names
- `search.open_shortcut`: shortcut that opens the search screen, e.g. `Control+M`
- `search.input_selector`: selector for the ID/Fundraiser search input
- `search.submit_selector`: selector for the search button
- `search.loaded_markers`: text markers proving the requested record is loaded
- `fields`: labels and output headers to extract

To add another field, add a new object to `fields`:

```json
{
  "key": "example_percent",
  "label": "Example %",
  "output_header": "Example %",
  "type": "percent"
}
```

To add another site, copy `config/sites/wesser.json`, edit it, then run:

```powershell
.\.venv\Scripts\python.exe .\wesser_strl_scraper.py `
  --config ".\config\sites\new-site.json" `
  --input ".\Input.xlsx" `
  --output ".\Output.xlsx"
```

## Local Artifacts

The scraper may create:

- `.browser-profile/` or a custom `--profile-dir`
- `*.checkpoint.json`
- output `.xlsx` or `.csv`

These are intentionally ignored by Git.
