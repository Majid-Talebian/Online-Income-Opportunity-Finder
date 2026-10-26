# Online Income Opportunity Finder

A local-first decision-support assistant for discovering and assessing online income opportunities. The Windows release uses Python and SQLite, stores auditable missions and source evidence, scores market research priority separately from execution fit, and creates a 14-section assessment with gates and a small validation plan. Its agents are deterministic software roles, not separate cloud LLMs.

The app does not require Floot or its AI credits. Fresh web searches still require an internet connection and a reachable search provider. Search results are leads, not verified demand or a promise of income. Economics are calculated only from user-entered values; commercial actions require the user's review.

## Quick start (Windows)

1. Install Python 3.10 or later.
2. Run `start_windows.bat`.
3. Open `http://127.0.0.1:8765`.
4. Configure and test the search provider; optionally configure local Ollama.

See the [Persian setup guide](README_FA.md), [architecture and decision rules](ARCHITECTURE_FA.md), and [provider connection guide](CONNECTIONS_FA.md).

The local database (`arman.db`) and personal profile (`company.json`) are excluded from Git. Do not commit credentials, personal data, or runtime databases to this public repository.

## Acceptance checks

Run `python -m unittest discover -v` for isolated backend checks. For the optional DOM acceptance suite install development dependencies with `npm install`, then run `npm run test:ui` (Node 22+, Python on PATH, port 8765 available). The application itself needs only Python. DOM tests use synthetic source fixtures and a temporary SQLite database; they do not establish live source coverage or visual browser acceptance. See [the phase acceptance report](PHASES_0_4_ACCEPTANCE.md) for open live-data and calibration requirements.
