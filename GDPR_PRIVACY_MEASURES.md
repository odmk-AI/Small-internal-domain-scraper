# GDPR And Private Data Protection Measures

This document explains how Small Internal Domain Scraper is designed to reduce privacy risk when processing internal records. It is technical and operational documentation, not legal advice. A company privacy/legal owner must still approve the concrete processing purpose, access rights, retention period, and legal basis.

## Regulatory Principles Reflected In The Design

The project is built around the following GDPR principles and obligations:

- Data minimisation: process only data necessary for the purpose.
- Purpose limitation: use the scraper only for the defined extraction task.
- Storage limitation: keep local outputs and checkpoints only as long as needed.
- Integrity and confidentiality: protect local browser profile, input, output, and checkpoint files.
- Data protection by design and by default: keep defaults narrow and local.
- Security of processing: apply appropriate technical and organisational measures.

References:

- GDPR Article 5 defines principles including purpose limitation, data minimisation, accuracy, storage limitation, and integrity/confidentiality: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- GDPR Article 25 requires data protection by design and by default, including measures such as pseudonymisation and limiting processing to what is necessary: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- GDPR Article 32 requires appropriate security of processing, including confidentiality, integrity, availability, and regular assessment of measures: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- European Commission guidance describes privacy by default as processing only necessary data, keeping it for a short period, and limiting accessibility: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/obligations/what-does-data-protection-design-and-default-mean_en

## Data Flow

```text
Local input XLSX
  -> local Python process
  -> local browser profile/session
  -> internal website search/detail page
  -> local parser extracts configured fields only
  -> local-only output directory with XLSX/CSV and optional local checkpoint
```

No intentional external transfer is performed by this project. The scraper itself does not send input files, output files, page text, HTML, screenshots, or extracted values to OpenAI, GitHub, or any other third party.

Important exception: the user’s normal browser/site interaction with the internal website still happens. The website may create its own access logs or audit logs.

## Data Categories

Expected input:

- Pseudonymous/internal ID such as `PseudoID`
- Or, when approved, `Fundraiser Number`

Expected output:

- Same ID column
- Configured extracted fields, currently:
  - `Individuelle StRL%`
  - `Individuelle Vorschuss%`

Data intentionally not written:

- Names
- Private addresses
- Email addresses
- Phone numbers
- Birth dates
- Tax identifiers
- Social security-like identifiers
- Bank details
- Full page text
- HTML dumps
- Screenshots
- Cookies or session tokens

## Implemented Technical Measures

### Local-Only Execution

The scraper runs on the user’s machine. It reads local input files and writes local output files. It does not use hosted scraping infrastructure.

### Configurable Minimal Extraction

Fields are explicitly listed in `config/sites/*.json`. The scraper extracts only configured labels and writes only configured output columns.


### Dedicated Local Output Directory

Generated output files, optional CSV exports, and checkpoints must be written inside the configured local output directory. The default is `local_outputs/`, which is ignored by Git. Bare output filenames are automatically resolved into this directory. Absolute output paths or relative traversal paths outside the configured output directory are rejected.

### Pseudonymous Input Support

The preferred input header is `PseudoID`. This allows the operating team to keep direct identity data outside this tool.

### Duplicate And Invalid Row Handling

The input reader:

- accepts only numeric IDs
- skips invalid rows
- de-duplicates IDs before scraping

This reduces unnecessary page access and avoids repeated processing of the same record.

### No Debug Dumps By Default

The code does not intentionally write:

- `document.body.innerText`
- page HTML
- screenshots
- console logs containing record data

### Strict Git Ignore Rules

`.gitignore` excludes local data and secrets-adjacent artifacts:

```text
.venv/
.browser-profile/
.wesser-browser-profile/
local_outputs/
*.xlsx
*.xls
*.csv
*.checkpoint.json
~$*
```

This is intended to prevent accidental commits of source data, outputs, checkpoints, local browser profile data, and Excel temporary files.

### Checkpoint Versioning

Checkpoints include:

- version
- site name
- field keys

If config changes materially, old checkpoints are ignored. This reduces stale or incompatible data reuse.

### Local Browser Profile Isolation

The scraper uses a dedicated local browser profile directory by default. This helps keep the automation session separate from a user’s normal browser profile.

## Organisational Measures Required Before Production Use

The software controls are not sufficient by themselves. The operating company should confirm:

- The user running the scraper is authorised to view each queried record.
- The processing purpose is documented and approved.
- The input list contains only IDs needed for that approved purpose.
- The local output directory has appropriate access controls and is not synced to uncontrolled cloud, email, chat, or shared drives.
- The output and checkpoint retention period is defined.
- The local browser profile is protected and deleted when no longer needed.
- Internal website scraping is allowed by company policy and the website owner.
- Any works council, HR, or employee monitoring requirements are considered where applicable.
- Logs and audit trails are reviewed for proportionality.

## Operational Checklist

Before running:

- Use an input file with only `PseudoID` where feasible.
- Do not include names, email addresses, addresses, or performance data in the input file.
- Store input in an approved local or company-controlled location and write output only into the configured local output directory.
- Confirm the user account has a legitimate need to access the records.
- Confirm `.gitignore` is active with `git status --ignored`.

During running:

- Run locally.
- Do not paste record data into chat tools.
- Do not enable debug logging of full page text.
- Do not take screenshots unless separately approved.
- Prefer visible/non-headless mode for validation only; use the same privacy controls either way.

After running:

- Validate the output contains only expected columns.
- Delete checkpoint files if resume is no longer required.
- Delete or protect the browser profile according to internal policy.
- Move output to the approved storage location only if required and approved.
- Delete local copies when no longer needed.
- Do not commit generated files.

## Residual Risks

Even with these controls, risk remains:

- `PseudoID` or `Fundraiser Number` can still be personal data if the company can map it back to a person.
- The local browser temporarily renders full record pages.
- The internal website may log every accessed record.
- Browser profile folders may contain session data.
- Output files still contain personal or pseudonymous data.
- The local output directory is protected by location and Git exclusion, but operating system access controls and disk encryption remain organisational requirements.
- A developer could weaken the controls by adding broad logging or committing ignored files with force.

These risks require organisational controls, access restrictions, and review.

## What This Project Does Not Guarantee

This project does not by itself guarantee:

- GDPR compliance
- a valid legal basis
- a valid works council/employee-representation approval
- permission to scrape the internal website
- correct role-based access in the source system
- encryption at rest for local files
- secure deletion
- prevention of all accidental misuse

It provides a privacy-conscious technical baseline that must be embedded in a compliant company process.

## Developer Rules

Developers changing this project should follow these rules:

1. Do not add logging of page body text, HTML, screenshots, cookies, or browser storage.
2. Do not commit real input, output, checkpoint, or browser profile files.
3. Keep site-specific selectors and labels in `config/sites/*.json` where possible.
4. Keep output columns limited to configured fields.
5. Treat `PseudoID` as personal data unless the company confirms it is truly anonymous.
6. Review `.gitignore` when adding new output formats.
7. Keep generated outputs and checkpoints constrained to the configured local output directory.
8. Add a privacy review note to pull requests that change extraction scope, logging, storage, or browser behavior.

## Recommended Pull Request Privacy Review

For each change, answer:

- Does this change add a new data field?
- Does this change broaden page access?
- Does this change write more data to disk?
- Does this change introduce logs, screenshots, or HTML dumps?
- Does this change affect checkpoint content?
- Does this change affect where output files are stored?
- Does `.gitignore` still block generated data?

If any answer is yes, request privacy/security review before production use.
