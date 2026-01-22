# Simple Icons CLI

A powerful, interactive command-line interface for [Simple Icons](https://simpleicons.org/).
Built with Python, Typer, Rich, and RapidFuzz.

## Features

- 🚀 **Interactive Shell**: Type `simple-icons` to enter a REPL with autocomplete and history.
- 🔍 **Fuzzy Search**: Typos? No problem. Use `dungeons` to find `dungeonsanddragons`.
- 🎨 **Image Processing**:
    - Convert to **PNG, ICO, JPG, PDF, ICNS** (macOS).
    - **Recolor** icons on the fly.
    - **Invert** colors (`--invert` for dark mode).
    - Set **Opacity** (`--opacity 0.5`).
    - Add **Backgrounds** (`--background ffffff`).
- 🤖 **Scripting Friendly**: Use `-s` (`--streamline`) for clean, machine-readable output.

## Installation

This project is managed with `uv`.

```bash
# Clone the repository
git clone https://github.com/yourusername/simple-icons-cli.git
cd simple-icons-cli

# Install dependencies
uv sync
```

## Usage

### Interactive Mode (Recommended)
Just run the tool without arguments:

```bash
uv run simple-icons
```

You will enter the shell:
```text
🚀 simple-icons > search google
🚀 simple-icons > download github --format png
```

### One-off Commands

**Search**
```bash
uv run simple-icons search "visual studio"
```

**Download**
```bash
# Basic SVG
uv run simple-icons download youtube

# Advanced Conversion
uv run simple-icons download apple --format png --size 512 --invert --opacity 0.8
```

**Scripting Mode**
```bash
# Clean output: "exported filename.ext"
uv run simple-icons -s download facebook -f png
```

## Dependencies

- **System**: `libcairo` (required for PNG/PDF conversion).
    - macOS: `brew install cairo`
    - Linux: `sudo apt install libcairo2`
- **Python**: `typer`, `rich`, `requests`, `cairosvg`, `pillow`, `rapidfuzz`, `prompt_toolkit`.

## License

MIT
