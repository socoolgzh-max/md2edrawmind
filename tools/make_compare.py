# -*- coding: utf-8 -*-
"""生成 docs/compare.png：两张真实产物并排对比。

左：普通 Markdown 导入（公式变成文字）
右：本工具产物（公式渲染成图片）

两张都是本项目流水线真实产出的 docx 渲染图，没有手绘。
用法: python tools/make_compare.py
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "compare")
DOCS = os.path.join(ROOT, "docs")

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def font(size):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_docx(docx, out_dir):
    """用 LibreOffice Kit 渲染 docx 首页"""
    node = None
    for c in [r"D:\Tool\DSharness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe",
              r"C:\Program Files\nodejs\node.exe"]:
        if os.path.exists(c):
            node = c
            break
    cli = r"D:\Tool\DSharness\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js"
    if not node or not os.path.exists(cli):
        raise SystemExit("需要 LibreOffice Kit 与 Node 22+ 才能渲染对比图")
    subprocess.run([node, cli, "render", "--input", docx, "--output-dir", out_dir,
                    "--pages", "1", "--dpi", "110"], capture_output=True, timeout=240)
    p = os.path.join(out_dir, "page-0001.png")
    if not os.path.exists(p):
        raise SystemExit("渲染失败: " + p)
    return p


def make_raw_docx(md_path, out_docx):
    """把 Markdown 里的公式去掉 $ 号，模拟"普通导入"—公式变成纯文字"""
    import re
    src = open(md_path, encoding="utf-8").read()
    plain = re.sub(r"\$([^$\n]+?)\$", r"\1", src)
    tmp = os.path.join(BUILD, "plain.md")
    os.makedirs(BUILD, exist_ok=True)
    open(tmp, "w", encoding="utf-8").write(plain)
    subprocess.run([sys.executable, "-m", "md2edrawmind", "convert", tmp, "-o", out_docx],
                   cwd=ROOT, capture_output=True, timeout=300)
    if not os.path.exists(out_docx):
        # 兼容"没有公式时不启动渲染"的分支
        subprocess.run([sys.executable, "-m", "md2edrawmind", "convert", tmp, "-o", out_docx],
                       cwd=ROOT, capture_output=True, timeout=300)
    return out_docx


def main():
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)

    fixture = os.path.join(ROOT, "tests", "fixture.md")
    good = os.path.join(BUILD, "good.docx")
    plain = os.path.join(BUILD, "plain.docx")

    print("[1/3] 生成两份 docx（美化版 / plain 版）")
    subprocess.run([sys.executable, "-m", "md2edrawmind", "convert", fixture, "-o", good],
                   cwd=ROOT, capture_output=True, timeout=300)
    make_raw_docx(fixture, plain)

    print("[2/3] 渲染成图")
    left = Image.open(render_docx(plain, os.path.join(BUILD, "lo-plain"))).convert("RGB")
    right = Image.open(render_docx(good, os.path.join(BUILD, "lo-good"))).convert("RGB")

    print("[3/3] 拼图")
    pad, gap, header = 28, 26, 58
    h = 900
    def fit(im):
        w = int(im.width * h / im.height)
        return im.resize((w, h), Image.LANCZOS)

    left, right = fit(left), fit(right)
    W = pad * 2 + left.width + gap + right.width
    H = pad * 2 + header + h
    canvas = Image.new("RGB", (W, H), (246, 248, 252))
    d = ImageDraw.Draw(canvas)

    f_title = font(26)
    d.text((pad, pad), "普通 Markdown 导入", font=f_title, fill=(220, 38, 38))
    d.text((pad + left.width + gap, pad), "md2edrawmind 产物", font=f_title, fill=(5, 150, 105))

    canvas.paste(left, (pad, pad + header))
    canvas.paste(right, (pad + left.width + gap, pad + header))

    d.rectangle([pad - 1, pad + header - 1, pad + left.width, pad + header + h],
                outline=(252, 165, 165), width=2)
    d.rectangle([pad + left.width + gap - 1, pad + header - 1,
                 pad + left.width + gap + right.width, pad + header + h],
                outline=(110, 231, 183), width=2)

    out = os.path.join(DOCS, "compare.png")
    canvas.save(out)
    print("完成 →", out, canvas.size, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
