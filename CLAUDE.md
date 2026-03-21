# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the script

```bash
python read_members.py
```

Requires a Python virtual environment (already present in `venv/`):

```bash
source venv/bin/activate
python read_members.py
```

## Project structure

- `read_members.py` — reads `members.csv` and prints each member's first and last name
- `members.csv` — data file with columns: `id`, `first_name`, `last_name`, `email`, `gender`, `ip_address`

## CSV column names

The script uses `first_name` and `last_name` as keys — these must match the CSV header exactly.
