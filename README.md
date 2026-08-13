# Anicorder

![GitHub Release](https://img.shields.io/github/v/release/spekdev/anicorder)

Anicorder is a terminal-based anime tracker built with Python and Textual. It uses MariaDB to store anime entries and provides a keyboard-driven TUI for managing your watchlist.

## Features

- Add anime to your collection
- Search anime by title
- Browse anime entries in a table
- Modify existing entries
- Remove anime entries
- Track:
	- Watch status
	- Episode progress
	- Time watched
- Paginated database results
- Duplicate-title protection
- Keyboard-driven Vim-style bindings

## Tech Stack & Requirements

- **Python 3.14.5**
- **Textual** — terminal user interface
- **MariaDB** — database
- **MariaDB Connector/Python** — database connectivity
- **uv** — Python project and virtual-environment management

## Database Schema

Anicorder uses a MariaDB database named `anicorder`.

### `anime`

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT` | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique anime identifier |
| `english_title` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` | English title of the anime |
| `status` | `ENUM('tba','tbw','watching','completed','dropped')` | `NOT NULL`, `DEFAULT 'watching'` | Current watch status |
| `episode` | `INT` | `NOT NULL`, `DEFAULT 1` | Current episode |
| `time_watched_in_seconds` | `INT` | `NOT NULL`, `DEFAULT 0` | Total recorded watch time in seconds |

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd anicorder
```

Install the Python dependencies:

```bash
uv sync
```

Ensure MariaDB is running, then create the database and table using the included schema:

```bash
mariadb -u root -p < setup/schema.sql
```

> [!TIP]
> Configure the database credentials in the application if your MariaDB setup differs from the default configuration.

## Running

Start Anicorder with:
```bash
uv run main.py
```
