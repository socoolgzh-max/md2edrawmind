# -*- coding: utf-8 -*-
"""编排整条流水线：Markdown → 公式图片 → Word。

每一步都通过 progress 回调汇报（GUI 用它显示进度）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import parser as md_parser
from .docx_writer import DocxBuilder, load_images
from .paths import node_modules_dir, tools_dir

Progress = Callable[[str, int], None]     # (消息, 0-100)


class PipelineError(RuntimeError):
    pass


# ---------------------------------------------------------------- 依赖探测
def find_node() -> Optional[str]:
    exe = shutil.which("node")
    if exe:
        return exe
    for cand in (
        r"D:\Envirment\nvm\nodejs\node.exe",
        r"C:\Program Files\nodejs\node.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs\node.exe"),
    ):
        if os.path.exists(cand):
            return cand
    return None


def find_chrome() -> Optional[str]:
    for cand in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ):
        if os.path.exists(cand):
            return cand
    for name in ("chrome", "msedge", "chromium"):
        exe = shutil.which(name)
        if exe:
            return exe
    return None


def tools_dir_js() -> str:
    """tools/*.js 的目录（兼容源码布局与 pip 安装布局）"""
    return tools_dir()


# ---------------------------------------------------------------- 结果
@dataclass
class ConvertResult:
    files: List[str]
    nodes: int
    formulas: int
    outline: List[str]
    missing: int
    work_dir: str


def _write_work(work_dir: str, root, title: str) -> int:
    """把解析结果写给渲染器和 Word 生成器"""
    os.makedirs(os.path.join(work_dir, "formula-png"), exist_ok=True)

    formulas: List[str] = []

    def dump(node):
        segs = []
        for s in node.segs:
            if s.type == "text":
                segs.append({"type": "text", "value": s.value})
            else:
                formulas.append(s.value)
                segs.append({"type": "math", "value": s.value, "display": s.display})
        return {
            "depth": node.depth,
            "kind": node.kind,
            "text": node.text,
            "segs": segs,
            "children": [dump(c) for c in node.children],
        }

    tree = {"title": title, "text": title, "depth": 0, "kind": "root", "segs": [], "children": [dump(c) for c in root.children]}
    json.dump(tree, open(os.path.join(work_dir, "doc-tree.json"), "w", encoding="utf-8"), ensure_ascii=False)
    with open(os.path.join(work_dir, "formulas.txt"), "w", encoding="utf-8") as fh:
        for i, tex in enumerate(formulas, 1):
            fh.write("%d\t%s\n" % (i, tex))
    return len(formulas)


def convert(
    md_path: str,
    out_path: str,
    work_dir: Optional[str] = None,
    mix: str = "tail",
    limit: int = 0,
    progress: Optional[Progress] = None,
    node_exe: Optional[str] = None,
    chrome_exe: Optional[str] = None,
) -> ConvertResult:
    def say(msg: str, pct: int) -> None:
        if progress:
            progress(msg, pct)

    md_path = os.path.abspath(md_path)
    out_path = os.path.abspath(out_path)
    if not os.path.exists(md_path):
        raise PipelineError("找不到输入文件：%s" % md_path)
    work_dir = os.path.abspath(work_dir or os.path.join(os.path.dirname(out_path), "_work"))
    os.makedirs(work_dir, exist_ok=True)

    node = node_exe or find_node()
    chrome = chrome_exe or find_chrome()

    say("解析 Markdown…", 5)
    md = open(md_path, encoding="utf-8").read()
    root, title = md_parser.parse(md, mix=mix)
    formula_count = _write_work(work_dir, root, title)

    outline = md_parser.to_outline(root, limit=0, title=title)
    total_nodes = sum(1 for _ in md_parser.iter_nodes(root))
    say("识别到 %d 个主题、%d 条公式" % (total_nodes, formula_count), 15)

    # 没有公式就不需要渲染
    if formula_count == 0:
        say("没有公式，直接生成 Word…", 70)
        builder = DocxBuilder({}, title)
        files = _save_docx(builder, root, out_path, limit, title)
        return ConvertResult(files, total_nodes, 0, outline, 0, work_dir)

    if not node:
        raise PipelineError("找不到 Node.js（渲染公式需要）。请安装 Node 18+ 后重试。")
    if not chrome:
        raise PipelineError("找不到 Chrome/Edge（把公式渲染成图片需要）。请安装后重试。")

    render_js = os.path.join(tools_dir_js(), "render.js")
    if not os.path.exists(render_js):
        raise PipelineError("工具缺失：%s" % render_js)
    if not os.path.isdir(os.path.join(node_modules_dir(), "mathjax-full")):
        raise PipelineError("缺少公式渲染依赖。请在工具目录执行：npm install mathjax-full pngjs\n"
                            "（或设置环境变量 MD2EDRAW_NODE_MODULES 指向已安装的 node_modules）")

    say("排版公式表…", 25)
    _run([node, render_js, "sheet", work_dir], "公式排版失败")

    say("渲染公式（浏览器无头截图）…", 45)
    sheet = os.path.join(work_dir, "sheet.png")
    if os.path.exists(sheet):
        os.remove(sheet)
    url = "file:///" + os.path.join(work_dir, "sheet.html").replace("\\", "/")
    _run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
          "--window-size=1600,14000", "--screenshot=%s" % sheet, url], "浏览器截图失败")
    if not os.path.exists(sheet):
        raise PipelineError("浏览器没有产出截图（sheet.png）")

    say("切分公式图片…", 65)
    _run([node, render_js, "slice", work_dir], "公式图片切分失败")

    say("生成 Word…", 85)
    images = load_images(work_dir)
    builder = DocxBuilder(images, title)
    files = _save_docx(builder, root, out_path, limit, title)

    result = ConvertResult(files, total_nodes, formula_count, outline, len(builder.missing), work_dir)
    for f in files:
        if not os.path.exists(f):
            raise PipelineError("Word 生成失败：%s" % f)
    say("完成", 100)
    return result


def _save_docx(builder: DocxBuilder, root, out_path: str, limit: int, title: str) -> List[str]:
    files: List[str] = []
    if limit and limit > 0:
        parts = DocxBuilder.split(root, limit)
        base, ext = os.path.splitext(out_path)
        for i, (prefix, part) in enumerate(parts, 1):
            path = "%s-第%d部分%s" % (base, i, ext)
            label = " › ".join(prefix) if prefix else ""
            head = "%s（第 %d/%d 部分）" % (title, i, len(parts))
            if label:
                head = "%s（%s，第 %d/%d 部分）" % (title, label, i, len(parts))
            builder.build(root, path, part_title=head, nodes=part)
            files.append(path)
    else:
        builder.build(root, out_path)
        files.append(out_path)
    return files


def _run(cmd: List[str], err_prefix: str, cwd: Optional[str] = None) -> None:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise PipelineError(err_prefix + "：超时")
    if proc.returncode != 0:
        tail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        msg = tail[-1] if tail else "退出码 %d" % proc.returncode
        raise PipelineError("%s：%s" % (err_prefix, msg))
