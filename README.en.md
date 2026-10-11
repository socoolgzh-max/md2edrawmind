<div align="center">

# md2edrawmind

**Turn AI-generated Markdown notes full of `$LaTeX$` into Word files your mind-map app imports — with every formula still readable.**

[中文说明](README.md) · English

[![CI](https://github.com/socoolgzh-max/md2edrawmind/actions/workflows/ci.yml/badge.svg)](https://github.com/socoolgzh-max/md2edrawmind/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Node](https://img.shields.io/badge/Node-18%2B-339933?logo=nodedotjs&logoColor=white)](package.json)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)](#known-limits)
[![Offline](https://img.shields.io/badge/100%25-offline-8b5cf6)](#features)

[Quick start](#quick-start) · [Features](#features) · [How it works](#how-it-works) · [Docs](#documentation) · [Roadmap](#roadmap)

</div>

## Interface

One drop zone, three secondary options under a hairline rule, one result row. No account, no upload, no cloud. It stays usable down to phone width.

![Interface](docs/gui.png)

<div align="center">

![Before / after](docs/compare.png)

</div>

> **The 10-second version.** You asked an LLM for a mind map of your revision notes. It gave you Markdown full of formulas. You imported it — and the formulas turned into `\lim_{n \to \infty} S_n = S` gibberish, or got flattened to `limn→∞Sn=S`, or the whole note came back in the wrong script.
>
> This tool converts that Markdown into a `.docx` where **every formula is a crisp rendered image** and **the heading hierarchy survives the import** — so the map you see is the map you wanted.

---

## Download

**Windows 10 / 11. Everything is bundled, nothing to install.**

[![Download installer](https://img.shields.io/badge/Download-installer%2043%20MB-b4531f?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/socoolgzh-max/md2edrawmind/releases/latest)

### Unblock the file first (required)

**Without this step, double-clicking the installer does nothing at all** and Windows shows no error: SmartScreen blocks it silently because the build is unsigned.

```powershell
Unblock-File .\md2edrawmind-1.0.0-setup.exe
.\md2edrawmind-1.0.0-setup.exe
```

Or in Explorer: right-click the installer, Properties, tick **Unblock** at the bottom of the General tab. If Windows still warns you, choose More info, then Run anyway.

### Install and use

Run the installer (per-user, no admin rights), then start it from the Start Menu. It opens its **own desktop window** (no console window appears), not a browser tab: drop a `.md` in, then download the result. Closing the window exits the app.

> [!IMPORTANT]
> **Double-click does nothing?** The build is not code-signed, so Windows marks the download as "from the internet" and SmartScreen may block it silently, with no error at all. Right-click the installer, open Properties, tick **Unblock** at the bottom of the General tab, then run it. If Windows still warns you, choose More info, then Run anyway.
>
> Or run `Unblock-File .\md2edrawmind-1.0.0-setup.exe` in PowerShell. The app never goes online and never uploads your notes; the source and build scripts are in this repo.

**Conversion failed, or double-click does nothing?** Startup and conversion steps are logged to:

```
%LOCALAPPDATA%\md2edrawmind\startup.log
```

It ships its own Python and Node runtime. Formula rendering uses the Chrome or Edge already on your machine. Prefer the command line? See [Quick start](#quick-start).

---

## The problem

Mind-map apps parse Markdown as *plain text*. They have no idea what `$...$` means.

We tested this the hard way — the full log is in [docs/FINDINGS.md](docs/FINDINGS.md). Summary:

| Route | What happens |
| --- | --- |
| Import Markdown | ✗ formulas stay literal text |
| Import HTML via "smart parse" | ✗ goes through a cloud AI: **simplified Chinese silently becomes traditional**, hierarchy collapses, formulas become tags |
| Native Word equations (OMML) | ✗ the Word importer does not understand OMML — it **flattens formulas into characters**: `limn→∞Sn=S` |
| Vector SVG formulas | ✗ the importer rejects SVG |
| **Render formulas to PNG → import Word locally** | ✓ formulas survive, hierarchy intact, nothing is rewritten |

There is one more trap: **a formula sitting in the middle of a topic's text gets filed as a "comment"**. This tool moves formulas to the *end* of each topic by default — the layout that actually works.

## Features

| | |
| --- | --- |
| **Formulas that survive** | MathJax v3 renders every `$...$` to an image at import-safe size — fractions, sums, integrals, limits all intact |
| **Hierarchy that survives** | writes `w:outlineLvl` (the flag outline importers actually read), not just indentation |
| **Local GUI** | `python -m md2edrawmind serve` → drag a `.md`, watch progress, download the `.docx` |
| **CLI** | `convert` / `serve` / `check` / `install-tools` — scriptable, CI-friendly |
| **100% offline** | no uploads, no accounts, no cloud AI: your notes never leave the machine |
| **No watermark** | exported formula images are not watermarked (see [Known limits](#known-limits)) |
| **Auto-split** | free tiers cap imports at 50 topics — `--limit 46` splits the output automatically |
| **Three layout modes** | `tail` (formula last), `own` (formula as its own sub-topic), `keep` (original order) |

## Quick start

```bash
git clone https://github.com/socoolgzh-max/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt && npm install     # python-docx, Pillow, mathjax-full, pngjs
python -m md2edrawmind check                       # verifies Python / Node / browser
```

Then either:

```bash
python -m md2edrawmind serve                       # GUI at http://127.0.0.1:8787
# or
python -m md2edrawmind convert notes.md            # → notes.docx
```

Finally: **EdrawMind → Import → Word → pick the `.docx`**.

The interface is one column: a drop zone, three secondary options under a hairline rule, and a result row. No account, no upload, no cloud. It stays usable down to 375px.

<details>
<summary><b>See the workflow (animated)</b></summary>

![demo](docs/demo.gif)

</details>

<details>
<summary><b>Install from PyPI instead</b></summary>

```bash
pip install md2edrawmind
md2edrawmind install-tools        # fetches the JS formula renderer (mathjax-full, pngjs)
md2edrawmind check
```

</details>

<details>
<summary><b>All CLI options</b></summary>

| Option | Meaning |
| --- | --- |
| `--mix tail` | **default** — text first, formulas moved to the end of the topic (most reliable) |
| `--mix own` | each formula becomes its own sub-topic |
| `--mix keep` | keep the original sentence order (mid-text formulas become comments) |
| `--limit N` | at most N topics per output file (auto-split; free tiers cap at 50) |
| `--outline` | also write a tab-indented plain-text outline as a fallback import route |
| `--work DIR` | where intermediate files (formula sheet, formula PNGs) go |

</details>

## How it works

```
notes.md
  │
  ├─ parser.py         headings/lists → topic tree; text vs formula; layout strategy
  │
  ├─ tools/render.js   MathJax v3 → SVG (glyphs as paths, no font dependency)
  │                    → every formula laid out on one precisely measured sheet
  │
  ├─ headless Chrome   a single screenshot renders all formulas at once
  │
  ├─ tools/render.js   slice the sheet into one trimmed PNG per formula
  │
  └─ docx_writer.py    w:outlineLvl hierarchy + inline pictures → .docx
```

No LaTeX distribution, no pandoc, no Office required — just Node and a browser for rendering.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/FINDINGS.md](docs/FINDINGS.md) | **Reverse-engineering log**: which import routes are local vs cloud, why OMML gets flattened, why `w:outlineLvl` matters, what lives inside `.emmx` |
| [docs/FAQ.md](docs/FAQ.md) | "formula became a comment", the 50-topic cap, watermark questions, troubleshooting |
| [CONTRIBUTING.md](CONTRIBUTING.md) | how to run the tests; how to add support for another app (with an evidence checklist) |
| [CHANGELOG.md](CHANGELOG.md) | release history |

## Known limits

> [!IMPORTANT]
> Formulas end up as **images** inside the map. They display perfectly but cannot be re-edited as equations, because the target app's Word importer does not support OMML. That is the app's limitation — this tool documents it rather than hiding it.

- Built and verified against **EdrawMind 12.2.2 on Windows**; other apps need their own format work ([issues welcome](https://github.com/socoolgzh-max/md2edrawmind/issues)).
- Formulas are watermark-free in PNG/JPG export, but **PDF export still carries the app's trial watermark** (app policy — a converter cannot bypass it).
- Multi-line environments (`aligned`, `cases`) currently render as a single line.
- Chrome/Edge is required for the render step; the screenshot canvas is fixed at 14000px tall, so very large notes should use `--limit` to split.

## Roadmap

- [x] GUI + CLI + PyPI packaging
- [x] `docs/FINDINGS.md` — reverse-engineering notes
- [x] A 113-formula stress example in `examples/`
- [ ] Adapter for a second target app (XMind / FreeMind), **after** measuring its import behaviour
- [ ] Multi-line formula environments (`aligned`, `cases`)
- [ ] macOS / Linux path detection and packaging

## Contributing

```bash
python tests/test_parser.py         # parser + docx unit tests (no browser needed)
python tests/smoke_gui.py 8899      # GUI end-to-end: upload → progress → download → verify
python -m md2edrawmind convert examples/考研数学-无穷级数.md -o build/check.docx
```

Fork → branch → PR. If you are adding support for another app, measure its import behaviour
first and record the evidence in `docs/FINDINGS.md` — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) — do whatever you want with it.
