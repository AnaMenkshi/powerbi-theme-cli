# PBI Theme CLI — AI-Powered Power BI Theme Engine



A command-line AI agent that reads your Power BI `.pbix` files locally and generates production-ready theme JSON files using a large language model. Runs entirely on your machine — no Azure, no Microsoft account, no cloud dependency.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXECUTION FLOW                           │
│                                                                 │
│  1. DISCOVERY                                                   │
│     pbi_client.py scans your disk for .pbix files              │
│     Reads Report/Layout (UTF-16-LE encoded ZIP entry)          │
│     Extracts page names and visual metadata                     │
│                                                                 │
│  2. PALETTE GENERATION  (3 modes)                               │
│     color_engine.py → Groq API (llama-3.3-70b-versatile)       │
│                                                                 │
│     [describe] → user inputs a vibe string                     │
│                  → LLM generates a full 18-key palette JSON    │
│                                                                 │
│     [browse]   → page type detected from page name keywords    │
│                  → curated palette library matched             │
│                  → user selects from 4 options                 │
│                                                                 │
│     [auto]     → LLM infers best palette from page name alone  │
│                                                                 │
│  3. THEME COMPILATION                                           │
│     theme_builder.py maps the palette to Power BI theme schema │
│     Output: valid JSON with dataColors, background,            │
│     foreground, tableAccent, good/neutral/bad                  │
│                                                                 │
│  4. DELIVERY                                                    │
│     [export] → saves theme_<page>.json to disk                 │
│     [apply]  → injects JSON into .pbix ZIP structure           │
│     [chat]   → free-form LLM session about the dashboard       │
│                                                                 │
│  5. IMPORT IN POWER BI DESKTOP                                  │
│     View → Themes → Browse for themes → select JSON            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
pbi-theme-cli/
├── pbi_agent.py        # Entry point — CLI loop and mode routing
├── color_engine.py     # Palette generation via Groq LLM (3 modes)
├── theme_builder.py    # Palette → Power BI theme JSON compiler
├── pbi_client.py       # Local .pbix reader (ZIP + UTF-16-LE parser)
├── requirements.txt
├── .env.example
└── .gitignore
```

### Module responsibilities

| Module | Role |
|--------|------|
| `pbi_agent.py` | CLI entry point, user interaction loop, mode dispatcher |
| `color_engine.py` | LLM prompt construction, palette parsing, curated library, color math |
| `theme_builder.py` | Compiles raw palette dict into Power BI-compatible theme JSON schema |
| `pbi_client.py` | Opens `.pbix` as ZIP, decodes `Report/Layout` (UTF-16-LE), extracts pages |

---

## Prerequisites

- Python 3.9+
- Power BI Desktop (local installation)
- A free [Groq API key](https://console.groq.com) — no credit card required

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/pbi-theme-cli.git
cd pbi-theme-cli
pip install -r requirements.txt
```

Set your API key — either as an environment variable:

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_..."

# Mac / Linux
export GROQ_API_KEY="gsk_..."
```

Or paste it directly in `pbi_agent.py` line 14:

```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_...")
```

---

## Usage

```bash
python pbi_agent.py
```

The agent will scan your system for `.pbix` files and present a numbered list. Select a file, then choose a mode:

```
──────────────────────────────────────────────────
MODES:
  1. describe  — describe a vibe, AI picks colors
  2. browse    — choose from curated palettes
  3. auto      — AI auto-detects best theme per page
  4. apply     — inject themes into your .pbix file
  5. export    — save theme JSON files (manual import)
  6. chat      — ask the AI about your dashboard
  7. quit
──────────────────────────────────────────────────
```

### Mode details

**Mode 1 — describe**
Prompt the LLM with a natural language vibe string. The model returns an 18-key palette covering background, canvas, chart colors (×6), table header/rows, KPI card, font, accent, and sentiment colors.

```
Vibe examples:
  "dark luxury navy gold"
  "fresh clean white and green"
  "minimal slate grey"
  "warm earthy amber and brown"
  "electric modern purple blue"
```

**Mode 2 — browse**
The agent detects your page type from keywords (sales, finance, marketing, operations, executive) and presents 4 hand-crafted palettes. Each palette is expanded into a full 18-key theme.

**Mode 3 — auto**
The LLM reads each page name and independently infers the most appropriate professional palette. Useful for multi-page reports with different business contexts.

**Mode 4 — apply**
Injects the generated theme JSON directly into the `.pbix` ZIP structure. A timestamped backup is created before any write operation.

> **Note:** Power BI Desktop version 1.28+ (Feb 2026) cryptographically signs `.pbix` files. If injection fails, use mode 5 instead.

**Mode 5 — export**
Saves `theme_<PageName>.json` files to disk. Import manually via:
`Power BI Desktop → View → Themes → Browse for themes`

**Mode 6 — chat**
Opens a persistent LLM session with full context of your pages and current themes. Ask for DAX measures, chart recommendations, layout advice, or design feedback.

---

## What the theme covers

Each generated JSON theme controls:

- Page background and canvas fill color
- 6 chart data colors (visually distinct, palette-matched)
- Table: header background, header font, base rows, alternating rows
- KPI cards: background, border, value color, label color
- Global font color
- Accent color
- Conditional formatting: positive / negative / neutral color coding
- Slicer headers and selection states
- Chart axis labels and gridlines

---

## Technical notes

**Why no Azure?**
The agent reads `.pbix` files directly as ZIP archives using Python's `zipfile` stdlib. The `Report/Layout` entry is UTF-16-LE encoded JSON. No Power BI REST API, no Azure AD token, no service principal needed.

**LLM model**
Uses `llama-3.3-70b-versatile` via Groq's inference API. Groq's free tier supports this model with no billing required.

**Palette format**
The LLM is prompted to return a strict 18-key JSON object. The `color_engine._safe_parse()` method handles malformed responses with a fallback palette.

---

## License

MIT — free to use, modify, and distribute.
