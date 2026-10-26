# Online Income Opportunity Finder

A local-first research assistant for discovering and assessing online income opportunities. The first release runs as a small Python and SQLite application on Windows. It can scan public RSS search results, keep an auditable record of each run, and optionally summarize an individual lead with Ollama running on the same computer.

The app does not require Floot or its AI credits. Fresh web searches still require an internet connection and a reachable search provider. Search results are discovery leads, not verified demand or a promise of income.

## Quick start (Windows)

1. Install Python 3.10 or later.
2. Run `start_windows.bat`.
3. Open `http://127.0.0.1:8765`.
4. Configure and test the search provider; optionally configure local Ollama.

See [the Persian setup and scope guide](README_FA.md) and [provider connection guide](CONNECTIONS_FA.md) for details.

The local database (`arman.db`) and personal profile (`company.json`) are excluded from Git. Do not commit credentials, personal data, or runtime databases to this public repository.
