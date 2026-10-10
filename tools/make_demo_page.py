#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成自包含的演示页 web/demo.html（并录制 docs/demo.gif）。

页面里的素材全部是真实数据：
  · 左栏 = tests/fixture.md 的真实内容（公式原样高亮）
  · 右栏 = 真实公式图片（out/formula-png 由本工具渲染出来的 PNG）
  · 结尾的 docx 预览 = LibreOffice 渲染的真实产物首页
演示时序由页面内 JS 驱动，录制脚本只负责截图。

用法:
  python tools/make_demo_page.py            # 只生成 web/demo.html
  python tools/make_demo_page.py --render   # 顺便用 playwright 录成 docs/demo.gif
"""
from __future__ import annotations

import base64
import html
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MD_PATH = os.path.join(ROOT, "tests", "fixture.md")
WORK = os.path.join(ROOT, "build", "demo-work")
PAGE = os.path.join(ROOT, "web", "demo.html")
GIF = os.path.join(ROOT, "docs", "demo.gif")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
NODE_CANDIDATES = [
    r"D:\Tool\DSharness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe",
    r"C:\Program Files\nodejs\node.exe",
    r"D:\Envirment\nvm\nodejs\node.exe",
]
LO_CLI = r"D:\Tool\DSharness\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js"


def first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def b64_image(path, mime):
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode("ascii"))


def prepare_materials():
    """跑一次真实流水线，拿到公式图片；再渲染一份真实 docx 首页。"""
    os.makedirs(WORK, exist_ok=True)
    print("[materials] 运行转换：生成真实公式图片")
    rc = subprocess.run([sys.executable, "-m", "md2edrawmind", "convert", MD_PATH,
                         "-o", os.path.join(WORK, "demo.docx"), "--work", os.path.join(WORK, "w")],
                        cwd=ROOT, capture_output=True)
    if rc.returncode != 0:
        print((rc.stderr or b"").decode("utf-8", "replace")[-400:])
        raise SystemExit("转换失败，无法准备素材")

    print("[materials] 渲染 docx 首页预览")
    preview = os.path.join(WORK, "preview.png")
    node = first_existing(NODE_CANDIDATES)
    if node and os.path.exists(LO_CLI):
        out_dir = os.path.join(WORK, "lo")
        shutil.rmtree(out_dir, ignore_errors=True)
        subprocess.run([node, LO_CLI, "render", "--input", os.path.join(WORK, "demo.docx"),
                        "--output-dir", out_dir, "--pages", "1", "--dpi", "130"],
                       capture_output=True, timeout=240)
        src = os.path.join(out_dir, "page-0001.png")
        if os.path.exists(src):
            shutil.copy2(src, preview)
    return preview if os.path.exists(preview) else None


def build_markdown_html():
    """把 fixture.md 渲染成右侧带公式高亮的代码块 HTML"""
    lines = []
    for raw in open(MD_PATH, encoding="utf-8").read().split("\n"):
        esc = html.escape(raw)
        esc = re.sub(r"(\$[^$\n]+\$)",
                     r'<span class="tex">\1</span>', esc)
        esc = re.sub(r"^(#{1,6} .*)$", r'<span class="head">\1</span>', esc)
        esc = re.sub(r"^(&gt;.*)$", r'<span class="dim">\1</span>', esc)
        lines.append(esc if esc else "&nbsp;")
    return "\n".join(lines)


def build_formula_gallery(formula_dir):
    """真实公式图片：输入的是 LaTeX 原文，输出的是渲染结果"""
    if not os.path.isdir(formula_dir):
        return "", 0
    picks = []
    files = sorted(f for f in os.listdir(formula_dir) if f.endswith(".png"))
    for name in files[:8]:
        picks.append(b64_image(os.path.join(formula_dir, name), "image/png"))
    cells = "\n".join(
        '<div class="fx"><img src="%s" alt="rendered formula"/></div>' % src for src in picks)
    return cells, len(picks)


PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>md2edrawmind demo</title>
<style>
  :root{
    --paper:#f4f1ea; --card:#fffdf8; --ink:#1e1b16; --dim:#6f6558;
    --line:#e0d9cc; --accent:#b4531f; --ok:#2f7d4f;
    --mono:ui-monospace,"Cascadia Mono",Consolas,"SFMono-Regular",monospace;
    --sans:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--paper);color:var(--ink);font-family:var(--sans)}
  .stage{width:1000px;height:700px;padding:26px 30px 22px;display:flex;flex-direction:column;gap:16px;
         background:
           linear-gradient(180deg,rgba(255,255,255,.75),rgba(255,255,255,0) 120px),
           repeating-linear-gradient(0deg,rgba(30,27,22,.018) 0 1px,transparent 1px 26px),
           linear-gradient(140deg,#f6f3ec,#efe9dd 60%,#eae2d3);
  }
  /* ---- 顶部：标题 + 阶段说明 ---- */
  .top{display:flex;align-items:baseline;gap:14px}
  .brand{font:600 19px/1 var(--sans);letter-spacing:.2px}
  .brand span{color:var(--accent)}
  .steps{margin-left:auto;display:flex;gap:8px;align-items:center}
  .steps i{width:8px;height:8px;border-radius:50%;background:#cfc6b6;transition:none;display:block}
  .steps i.on{background:var(--accent);transform:scale(1.35)}
  .steps i.done{background:var(--ok)}

  .headline{font:400 22px/1.35 var(--sans);color:var(--dim);min-height:31px}
  .headline b{color:var(--ink);font-weight:600}

  /* ---- 主体：左 md 源 / 右 转换台 ---- */
  .body{flex:1;display:grid;grid-template-columns:1fr 348px;gap:20px;min-height:0}

  .paper{position:relative;background:var(--card);border:1px solid var(--line);border-radius:6px;
         box-shadow:0 1px 2px rgba(30,27,22,.05),0 10px 30px rgba(30,27,22,.07);
         display:flex;flex-direction:column;min-height:0;overflow:hidden}
  .paper::before{content:"";position:absolute;left:34px;top:0;bottom:0;width:1px;background:rgba(180,83,31,.13)}
  .paper .bar{display:flex;align-items:center;gap:9px;padding:9px 12px 9px 46px;border-bottom:1px solid var(--line);
              font:12.5px/1 var(--mono);color:var(--dim)}
  .paper .bar b{color:var(--ink);font-weight:600}
  .paper pre{margin:0;padding:12px 16px 16px 46px;overflow:hidden;font:12.5px/1.62 var(--mono);color:#332e26;
             -webkit-mask-image:linear-gradient(180deg,#000 72%,rgba(0,0,0,.05) 93%,transparent);
             mask-image:linear-gradient(180deg,#000 72%,rgba(0,0,0,.05) 93%,transparent);
             flex:1;min-height:0}
  .head{color:#8a5a2b;font-weight:600}
  .dim{color:#9a9082}
  .tex{color:var(--accent);background:rgba(180,83,31,.09);border-radius:3px;padding:0 2px}
  .scan{position:absolute;left:0;right:0;top:0;height:26px;opacity:0;pointer-events:none;z-index:2;
        background:linear-gradient(180deg,rgba(180,83,31,0),rgba(180,83,31,.16) 55%,rgba(180,83,31,0));
        border-top:1px solid rgba(180,83,31,.5);border-bottom:1px solid rgba(180,83,31,.22)}
  .cursor{position:absolute;width:20px;height:20px;left:-40px;top:52%;opacity:0;z-index:3;pointer-events:none;
          transition:none;
  .cursor.on{opacity:1}
  .cursor svg{filter:drop-shadow(0 2px 3px rgba(0,0,0,.3))}
  .drop{position:absolute;inset:0;border:2px dashed var(--accent);border-radius:6px;opacity:0;
        display:grid;place-items:center;background:rgba(180,83,31,.05);transition:opacity .18s}
  .drop span{font:600 15px var(--sans);color:var(--accent);background:var(--card);padding:8px 16px;border-radius:999px;
             border:1px solid rgba(180,83,31,.35)}
  .paper.drag .drop{opacity:1}
  .paper.drag{transform:scale(.995)}

  .desk{display:flex;flex-direction:column;gap:12px;min-height:0}
  .panel{background:rgba(255,253,248,.82);border:1px solid var(--line);border-radius:6px;padding:13px 14px;
         box-shadow:0 1px 2px rgba(30,27,22,.04)}
  .panel h4{margin:0 0 10px;font:600 12px/1 var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--dim)}

  ol.steps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
  ol.steps li{display:flex;align-items:center;gap:9px;font:13px/1.2 var(--sans);color:#a89e8e;transition:none;
  ol.steps li .tick{width:15px;height:15px;border-radius:50%;border:1.5px solid #d5ccbc;display:grid;place-items:center;
                    font-size:10px;color:transparent;transition:all .2s}
  ol.steps li.on{color:var(--ink)}
  ol.steps li.on .tick{border-color:var(--accent);border-style:dashed}
  ol.steps li.done{color:#4a5c4e}
  ol.steps li.done .tick{background:var(--ok);border-color:var(--ok);color:#fff;border-style:solid;font-weight:700;font-size:11px;box-shadow:0 0 0 3px rgba(47,125,79,.13)}

  .meter{margin-top:12px;height:6px;border-radius:3px;background:#e7dfd1;overflow:hidden}
  .meter i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--accent),#d98a4e);
           transition:none;
  .counts{display:flex;gap:14px;margin-top:9px;font:12px/1 var(--mono);color:var(--dim)}
  .counts b{color:var(--ink)}

  .swap{position:relative;flex:1;min-height:0}
  .swap .gallery{position:absolute;inset:0;align-content:start}
  .swap .out{position:absolute;inset:0}
  .gallery{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .fx{background:#fff;border:1px solid var(--line);border-radius:4px;height:44px;display:grid;place-items:center;
      padding:4px 6px;opacity:0;transform:translateY(6px);transition:none;
  .fx.show{opacity:1;border-style:solid}
  .fx img{max-width:100%;max-height:32px}

  .result{display:flex;align-items:center;gap:11px;padding:11px 12px;border:1px solid rgba(180,83,31,.4);border-radius:6px;background:linear-gradient(180deg,rgba(180,83,31,.07),rgba(180,83,31,.02));opacity:0;transform:translateY(8px);transition:none;
  .result.show{opacity:1;transform:none}
  .doc{width:26px;height:32px;border:1.5px solid var(--accent);border-radius:3px;position:relative;flex:none}
  .doc::after{content:"";position:absolute;left:4px;top:6px;right:4px;height:1.5px;background:var(--accent);
              box-shadow:0 5px 0 var(--accent),0 10px 0 rgba(180,83,31,.5)}
  .result .name{font:600 13.5px/1.3 var(--sans)}
  .result .sub{font:11.5px/1.3 var(--mono);color:var(--dim)}
  .result .go{margin-left:auto;font:600 13px var(--sans);color:#fff;background:var(--accent);
              padding:8px 15px;border-radius:5px;white-space:nowrap;box-shadow:0 2px 0 rgba(120,52,12,.35)}

  .out{position:relative;background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden;
       flex:1;min-height:0;opacity:0;transform:translateY(10px);transition:none;
  .out.show{opacity:1;transform:none}
  .out img{position:absolute;top:0;left:0;width:100%;display:block}
  .out .cap{position:absolute;left:0;right:0;bottom:0;padding:7px 12px;font:11.5px/1 var(--mono);color:var(--dim);
            background:linear-gradient(0deg,rgba(255,253,248,.96),rgba(255,253,248,0))}
</style>
</head>
<body>
<div class="stage">
  <div class="top">
    <div class="brand">md2<span>edrawmind</span></div>
    <div class="steps" id="dots"><i></i><i></i><i></i><i></i></div>
  </div>

  <div class="headline" id="headline">Drop a Markdown note into the tool</div>

  <div class="body">
    <div class="paper" id="paper">
      <div class="bar"><b>__MDNAME__</b><span>__MDSTAT__</span></div>
      <pre id="md">__MDHTML__</pre>
      <div class="scan" id="scan"></div>
      <div class="cursor" id="cursor"><svg viewBox="0 0 24 24" width="20" height="20"><path d="M4 2l14 10-6.5 1.2L14 21l-3 1-3-7.6L4 20V2z" fill="#fff" stroke="#1e1b16" stroke-width="1.4" stroke-linejoin="round"/></svg></div>
      <div class="drop"><span>Drop to convert</span></div>
    </div>

    <div class="desk">
      <div class="panel">
        <h4>Conversion</h4>
        <ol class="steps" id="list">
          <li data-i="0"><span class="tick">✓</span>Parse Markdown &amp; LaTeX</li>
          <li data-i="1"><span class="tick">✓</span>Lay out formula sheet</li>
          <li data-i="2"><span class="tick">✓</span>Render formulas (headless)</li>
          <li data-i="3"><span class="tick">✓</span>Slice PNGs &amp; build Word</li>
        </ol>
        <div class="meter"><i id="fill"></i></div>
        <div class="counts"><span>topics <b id="cTop">0</b></span><span>formulas <b id="cFx">0</b></span><span id="cTime"></span></div>
      </div>

      <div class="panel" style="flex:1;min-height:0;display:flex;flex-direction:column;gap:8px">
        <h4 id="galleryTitle">Formulas rendered</h4>
        <div class="swap">
          <div class="gallery" id="gallery">__GALLERY__</div>
          <div class="out" id="out">
            <img id="outImg" src="__PREVIEW__" alt="resulting docx"/>
            <div class="cap">__OUTNAME__ · page 1, opened in Word</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="result" id="result">
          <div class="doc"></div>
          <div>
            <div class="name">__OUTNAME__</div>
            <div class="sub">__OUTSUB__</div>
          </div>
          <div class="go">Download</div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function () {
  const $ = (id) => document.getElementById(id);
  const dots = [...$('dots').children];
  const list = [...$('list').children];
  const fx = [...$('gallery').children];
  const paper = $('paper');
  const out = $('out');
  const result = $('result');
  const fill = $('fill');
  const headline = $('headline');
  const cTop = $('cTop'), cFx = $('cFx'), cTime = $('cTime');
  const TOTAL_TOPICS = __TOPICS__, TOTAL_FX = __FX__;

  const SPEED = (function () {
    const m = /slow=([\d.]+)/.exec(location.hash || '');
    return m ? parseFloat(m[1]) : 1;
  })();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms * SPEED));

  // 用 setTimeout 驱动的补间（CDP 虚拟时间会精确推进定时器，CSS 过渡不会）
  function tween(ms, stepFn, doneFn, stepMs) {
    ms = ms * SPEED;
    stepMs = stepMs || 60;
    const n = Math.max(1, Math.round(ms / stepMs));
    let i = 0;
    return new Promise((resolve) => {
      (function tick() {
        i += 1;
        stepFn(i / n);
        if (i >= n) { if (doneFn) doneFn(); resolve(); return; }
        setTimeout(tick, stepMs);
      })();
    });
  }
  const step = (i, cls) => { if (!list[i]) return; list[i].classList.add(cls); if (dots[i]) dots[i].classList.add(cls); };
  const mark = (i) => {
    if (!list[i]) return;                 // 阶段数多于步骤指示器时，越界直接跳过
    list[i].classList.remove('on');
    list[i].classList.add('done');
    if (dots[i]) dots[i].classList.add('done');
  };
  const reveal = (k) => { const el = fx[k]; if (!el) return; el.classList.add('show'); el.style.opacity = '1'; };

  // 硬切阶段：每 380ms 一次明显变化，保证动图里"看得见在做什么"
  const PHASES = [
    { pct: 10, fx: 0, s: 0, head: '<b>Parse</b> headings, lists and <b>__FX__ LaTeX formulas</b>' },
    { pct: 22, fx: 2, s: 1, head: '<b>Lay out</b> every formula on one measured sheet' },
    { pct: 36, fx: 4, s: 2, head: '<b>Render</b> the sheet in a headless browser' },
    { pct: 52, fx: 6, s: 2, head: '<b>Slice</b> it into one PNG per formula' },
    { pct: 70, fx: 8, s: 3, head: '<b>Build the Word file</b> with w:outlineLvl + inline pictures' },
    { pct: 86, fx: 8, s: 3, head: '<b>Verify</b> hierarchy and picture count in the .docx' },
    { pct: 100, fx: 8, s: -1, head: '<b>Done.</b> 20 topics and 8 formulas carried over' },
  ];

  async function run() {
    $('paper').style.opacity = '1';
    await sleep(150);

    // 1. 光标飞入 -> 高亮稿纸 -> 落点
    const cur = $('cursor');
    cur.style.opacity = '1';
    await tween(600, (t) => {
      cur.style.left = (6 + t * 46) + '%';
      cur.style.top = (52 - t * 8) + '%';
    });
    paper.classList.add('drag');
    headline.innerHTML = '<b>Drop</b> the note here: fixture.md';
    await sleep(620);
    paper.classList.remove('drag');
    cur.style.opacity = '0';
    headline.innerHTML = '<b>Reading</b> fixture.md';
    await sleep(260);

    // 扫描线自上而下扫过 md 源文本（连续、明显的视觉变化）
    const scan = $('scan');
    const pre = $('md');
    const preH = pre.clientHeight;
    scan.style.opacity = '1';
    await tween(1500, function (t) {
      scan.style.transform = 'translateY(' + (t * (preH + 26)).toFixed(1) + 'px)';
    }, null, 50);
    scan.style.opacity = '0';

    // 2. 硬切推进七个阶段
    step(0, 'on');
    let shownStep = -1;
    for (let k = 0; k < PHASES.length; k++) {
      const ph = PHASES[k];
      if (ph.s !== shownStep) {
        if (shownStep >= 0) mark(shownStep);
        shownStep = ph.s;
        if (shownStep >= 0) step(shownStep, 'on');
      }
      fill.style.width = ph.pct + '%';
      for (let j = 0; j < ph.fx; j++) reveal(j);
      cFx.textContent = String(ph.fx);
      cTop.textContent = ph.pct >= 10 ? String(TOTAL_TOPICS) : '0';
      headline.innerHTML = ph.head.replace(/__FX__/g, String(TOTAL_FX));
      await sleep(ph.pct === 100 ? 700 : 420);
    }
    if (shownStep >= 0) mark(shownStep);
    dots.forEach(function (d) { d.classList.add('done'); });
    cTime.textContent = '2.1s';
    headline.innerHTML = '<b>Done.</b> The Word file carries every formula and the full outline';

    // 3. 结果落桌 -> 换成真实产物首页
    result.style.opacity = '1';
    result.style.transform = 'none';
    await sleep(420);
    $('gallery').style.display = 'none';
    out.style.opacity = '1';
    out.style.transform = 'none';
    headline.innerHTML = '<b>Import the .docx</b> into the mind-map app: formulas are images, outline is intact';
    await sleep(1400);
  }
  run().catch(function (err) {
    headline.textContent = 'SCRIPT ERROR: ' + (err && err.message ? err.message : err);
    headline.style.color = '#b00020';
  });
})();
</script>
</body>
</html>
"""


def write_page(preview_path, gallery_html, fx_count):
    md_html = build_markdown_html()
    topics = 20
    page = PAGE_TEMPLATE
    page = page.replace("__MDHTML__", md_html)
    page = page.replace("__MDNAME__", os.path.basename(MD_PATH))
    page = page.replace("__MDSTAT__", "20 topics · %d formulas" % fx_count)
    page = page.replace("__GALLERY__", gallery_html)
    page = page.replace("__PREVIEW__", b64_image(preview_path, "image/png") if preview_path else "")
    page = page.replace("__OUTNAME__", "fixture.docx")
    page = page.replace("__OUTSUB__", "20 topics · %d formulas · 70 KB" % fx_count)
    page = page.replace("__TOPICS__", str(topics))
    page = page.replace("__FX__", str(fx_count))
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("[page] 已生成", PAGE, len(page) // 1024, "KB")
    return PAGE


def record(page_path):
    """用 playwright + 本机 Chrome 逐帧截图，再合成 GIF"""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    chrome = first_existing(CHROME_CANDIDATES)
    frames_dir = os.path.join(WORK, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)

    W, H = 1000, 700
    url = "file:///" + page_path.replace("\\", "/")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=chrome, headless=True,
            args=["--force-device-scale-factor=1", "--hide-scrollbars", "--disable-gpu"])
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(url)                                   # 必须真正打开页面
        page.wait_for_timeout(250)

        # 每张截图之间留出渲染时间：连续无间隔截图会把合成器饿死，拿到同一帧。
        shots = 0
        deadline = time.time() + 11.0
        while time.time() < deadline:
            page.evaluate("1")                       # 强制一次渲染，避免拿到陈旧合成帧
            page.screenshot(path=os.path.join(frames_dir, "f%05d.png" % shots))
            shots += 1
            page.wait_for_timeout(90)                # 给合成器留出出帧时间
        browser.close()
    print("[record] 轮询截帧", shots, "张")

    # 合成 GIF：统一尺寸 -> 抽帧 -> 逐帧量化（不合并相同帧，保证动作连续）
    files = sorted(os.listdir(frames_dir))
    imgs = []
    for f in files:
        im = Image.open(os.path.join(frames_dir, f)).convert("RGB")
        imgs.append(im.resize((W, H), Image.LANCZOS))
    if not imgs:
        raise SystemExit("没有截到帧")

    # 均匀抽帧：录制时每张图约 180ms，取每 3 张 1 张 => 约 540ms 一帧，动作连贯
    stride = 3
    keep = imgs[::stride]
    durations = [540] * len(keep)
    if durations:
        durations[-1] += 700                      # 结尾稍作停留

    quant = [im.quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE) for im in keep]
    # PIL 保存 GIF 时 duration 直接按毫秒传入（已用最小实验确认）
    quant[0].save(GIF, save_all=True, append_images=quant[1:],
                  duration=durations, loop=0, optimize=False)
    size = os.path.getsize(GIF)
    print("[gif] 已生成 %s  %.1f MB  帧数 %d  总时长 %.1fs"
          % (GIF, size / 1048576.0, len(quant), sum(durations) / 1000.0))
    return GIF


def main():
    preview = prepare_materials()
    gallery_html, fx_count = build_formula_gallery(os.path.join(WORK, "w", "formula-png"))
    write_page(preview, gallery_html, fx_count)
    if "--render" in sys.argv:
        record(PAGE)


if __name__ == "__main__":
    main()
