# md2edrawmind

**Turn AI-generated Markdown notes that contain LaTeX formulas into Word files EdrawMind can import — with every formula still rendered, hierarchy intact, 100% offline.**

[中文说明](README.zh-CN.md) · English

[![CI](https://github.com/socoolgzh-max/md2edrawmind/actions/workflows/ci.yml/badge.svg)](https://github.com/socoolgzh-max/md2edrawmind/actions/workflows/ci.yml)

![demo](docs/demo.gif)

## The problem

Ask any LLM for a "mind map" of your revision notes and you get Markdown full of `$...$` formulas.
Import that into a mind-mapping app and **the formulas die**:

| Import route | Result |
| --- | --- |
| Import Markdown | ❌ Markdown-only parser, `$...$` stays literal text |
| Import HTML via "smart parse" | ❌ goes through a cloud AI: **simplified Chinese gets converted to traditional**, hierarchy lost, formulas become tags |
| Word's native equations (OMML) | ❌ its Word importer does not understand OMML and **flattens formulas into characters** (`limn→∞Sn=S`) |
| Vector SVG formulas | ❌ the importer rejects SVG |
| **Render formulas to PNG + import Word locally** | ✅ **formulas survive**, and image-form formulas are exported without a watermark |

There is also a quirk worth knowing: **a formula sitting in the middle of a topic's text is treated as a "comment"**. This tool therefore moves formulas to the *end* of each topic by default — the layout that was verified to work.

## Requirements

**From source (recommended while the project is young):**

```bash
git clone https://github.com/socoolgzh-max/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt     # python-docx + Pillow
npm install                         # mathjax-full + pngjs (formula rendering)
python -m md2edrawmind check        # self-check
```

**From PyPI** (the JS renderer is not shipped in the wheel, so install it once):

```bash
pip install md2edrawmind
md2edrawmind install-tools          # runs npm install for the bundled renderer
md2edrawmind check
```

You also need **Google Chrome or Microsoft Edge** (headless screenshot; auto-detected)
and **Node.js 18+**.

## Usage

### GUI (recommended)

```bash
python -m md2edrawmind serve
```

Opens `http://127.0.0.1:8787` — drag in a `.md`, watch the progress, download the `.docx`,
then in EdrawMind use **Import → Word**.

### CLI

```bash
python -m md2edrawmind convert notes.md                  # writes notes.docx
python -m md2edrawmind convert notes.md -o map.docx --outline
python -m md2edrawmind convert notes.md --limit 46       # auto-split for the 50-topic import cap
```

| Option | Meaning |
| --- | --- |
| `--mix tail` | **default**. Text first, formulas moved to the end of the topic (most reliable) |
| `--mix own` | Each formula becomes its own sub-topic |
| `--mix keep` | Keep the original sentence order (mid-text formulas become comments) |
| `--limit N` | At most N topics per output file (EdrawMind free tier caps imports at 50) |
| `--outline` | Also export a plain-text outline (tab-indented) as a fallback import route |

## How it works

```
notes.md
  ├─ parser.py        parse headings/lists, split text vs formulas, apply placement strategy
  ├─ render.js        MathJax → SVG (glyphs converted to paths, no font dependency)
  │                   → lay every formula out on one precisely-measured sheet
  ├─ headless Chrome  screenshot the whole sheet in one shot
  ├─ render.js slice  cut the sheet into one PNG per formula (whitespace trimmed)
  └─ docx_writer.py   write w:outlineLvl hierarchy + inline formula pictures
```

## Known limits

- Tuned for **EdrawMind's import behaviour**; other mind-map apps (XMind, MindManager) need their own format work.
- Formulas live as **pictures** in the map, so they are not re-editable equations (EdrawMind's Word import does not support OMML — that is its limitation, not this tool's).
- Picture formulas are watermark-free in PNG/JPG export, but **PDF export still carries the app's trial watermark**.
- The screenshot step depends on window height; for very long formula sheets increase `--window-size` in `tools/render.js`.

## Learn more

| Document | What's inside |
| --- | --- |
| [docs/FINDINGS.md](docs/FINDINGS.md) | **Reverse-engineered notes** on how EdrawMind imports files: which routes are local vs cloud AI, why OMML gets flattened, why `w:outlineLvl` matters, and what is inside `.emmx` |
| [docs/FAQ.md](docs/FAQ.md) | "Formula became a comment", the 50-topic cap, watermark questions, troubleshooting |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to run tests and how to add support for another app |

## Development

```bash
python -m md2edrawmind check          # environment self-check
python tests/test_parser.py           # parser / docx unit tests
python tests/smoke_gui.py 8899        # GUI end-to-end smoke test (upload → progress → download → verify)
python tools/make_demo_gif.py         # regenerate docs/demo.gif
node tools/render.js tex2svg work     # vector-only formula export (no browser needed)
```

## License

MIT
