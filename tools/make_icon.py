# -*- coding: utf-8 -*-
"""生成应用图标 docs/icon.ico（多尺寸）与安装前说明 docs/install-notes.txt。

图标与界面左上角标识同一套视觉：深墨底、圆角、三个分支节点。
用 Chrome 无头渲染 SVG 再转 ICO，避免引入额外绘图依赖。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = os.path.join(ROOT, "docs", "icon.ico")
NOTES = os.path.join(ROOT, "docs", "install-notes.txt")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

INK = "#1d1a15"
SURFACE = "#faf8f4"

SVG = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  html,body{{margin:0;padding:0;background:transparent}}
  .tile{{width:256px;height:256px;border-radius:58px;background:{ink};
         display:grid;place-items:center}}
  svg{{display:block}}
</style></head><body>
<div class="tile">
  <svg width="168" height="168" viewBox="0 0 24 24" fill="none">
    <path d="M7.4 12h3.1M13 8.2l2.6-1.9M13 15.8l2.6 1.9"
          stroke="{surface}" stroke-width="1.5" stroke-linecap="round" opacity=".9"/>
    <circle cx="5" cy="12" r="2.9" fill="{surface}"/>
    <circle cx="18" cy="5.4" r="2.3" fill="{surface}" opacity=".72"/>
    <circle cx="18" cy="12" r="2.3" fill="{surface}" opacity=".88"/>
    <circle cx="18" cy="18.6" r="2.3" fill="{surface}" opacity=".72"/>
  </svg>
</div></body></html>
"""

NOTES_TEXT = """md2edrawmind 会把带 LaTeX 公式的 Markdown 笔记，转成思维导图软件（EdrawMind 等）能直接导入的 Word 文件。

安装后会创建开始菜单快捷方式（可选桌面快捷方式）。运行程序会在本机启动一个小服务，并自动在浏览器里打开操作界面。

需要你机器上已安装 Chrome 或 Edge 之一：公式要渲染成图片，这一步用浏览器完成。Windows 通常自带 Edge，所以一般不用额外安装。

程序全程离线，不联网、不上传任何笔记内容。卸载时可通过开始菜单里的「卸载 md2edrawmind」完成。
"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("找不到 Chrome / Edge，无法渲染图标")


def render_icon() -> None:
    from PIL import Image

    chrome = find_chrome()
    tmp = tempfile.mkdtemp(prefix="m2e-icon-")
    html = os.path.join(tmp, "icon.html")
    png = os.path.join(tmp, "icon.png")
    with open(html, "w", encoding="utf-8") as fh:
        fh.write(SVG.format(ink=INK, surface=SURFACE))

    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--no-first-run", "--default-background-color=00000000",
                    "--window-size=256,256", "--virtual-time-budget=1500",
                    "--screenshot=" + png, "file:///" + html.replace("\\", "/")],
                   capture_output=True, timeout=120)
    if not os.path.exists(png):
        raise SystemExit("Chrome 没有生成图标 PNG")

    img = Image.open(png).convert("RGBA")
    if img.size != (256, 256):
        img = img.resize((256, 256), Image.LANCZOS)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ICON, format="ICO", sizes=sizes)
    print("[icon] %s  %d 字节  尺寸 %s" % (ICON, os.path.getsize(ICON), sizes))


def write_notes() -> None:
    with open(NOTES, "w", encoding="utf-8") as fh:
        fh.write(NOTES_TEXT)
    print("[notes] %s" % NOTES)


if __name__ == "__main__":
    render_icon()
    write_notes()
    sys.exit(0)
