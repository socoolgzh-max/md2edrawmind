# -*- coding: utf-8 -*-
"""Markdown（含 LaTeX）→ 可导入 EdrawMind 的 Word。

纯标准库 + python-docx。解析产出一棵"主题树"：
  - # / ## / ###  → 层级
  - - / * 列表     → 层级（按缩进）
  - $...$ / $$...$$ → 公式（交给渲染器出图）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------- 公式切分
MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$", re.S)


@dataclass
class Seg:
    """一段内容：文字或公式"""
    type: str                 # 'text' | 'math'
    value: str
    display: bool = False


@dataclass
class Node:
    kind: str                 # 'heading' | 'bullet'
    depth: int                # 1 起
    segs: List[Seg] = field(default_factory=list)
    children: List["Node"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(s.value for s in self.segs if s.type == "text").strip()

    @property
    def math(self) -> List[str]:
        return [s.value for s in self.segs if s.type == "math"]


def strip_emphasis(s: str) -> str:
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(^|\W)\*(?!\s)([^*]+?)\*(?=\W|$)", r"\1\2", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def split_math(raw: str) -> List[Seg]:
    segs: List[Seg] = []
    last = 0
    for m in MATH_RE.finditer(raw):
        if m.start() > last:
            segs.append(Seg("text", raw[last:m.start()]))
        if m.group(1) is not None:
            segs.append(Seg("math", m.group(1).strip(), True))
        else:
            segs.append(Seg("math", m.group(2).strip(), False))
        last = m.end()
    if last < len(raw):
        segs.append(Seg("text", raw[last:]))
    if not segs:
        segs.append(Seg("text", raw))
    return segs


# ---------------------------------------------------------------- 解析
class Parser:
    """把 Markdown 解析成主题树。

    混排策略 mix:
      'tail'  —— 文字在前，公式统一挪到末尾（EdrawMind 里最稳，推荐）
      'own'   —— 公式单独成为一条子主题
      'keep'  —— 保持原句顺序（公式夹在中间会被 EdrawMind 当批注）
    """

    def __init__(self, mix: str = "tail"):
        self.mix = mix
        self.root = Node("heading", 0)
        self.root.segs = []
        self.stack: List[Node] = [self.root]
        self.current: Optional[Node] = self.root
        self.title = "思维导图"

    # ---------- 公开入口 ----------
    def parse(self, md: str) -> Node:
        md = md.replace("\r\n", "\n")
        m = re.search(r"^#\s+(.+)$", md, re.M)
        if m:
            self.title = strip_emphasis(m.group(1).strip())
        for raw in md.split("\n"):
            line = raw.replace("\t", "  ")
            if not line.strip() or re.match(r"^-{3,}\s*$", line.strip()):
                continue
            h = re.match(r"^(#{1,6})\s+(.*)$", line)
            if h:
                self._heading(len(h.group(1)), h.group(2))
                continue
            b = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
            if b:
                self._bullet(len(b.group(1)), b.group(2))
                continue
            if self.current is not None:                      # 续行
                self.current.segs.append(Seg("text", " "))
                self.current.segs.extend(split_math(strip_emphasis(line.strip())))
        self._normalize(self.root, 0)
        return self.root

    # ---------- 内部 ----------
    def _heading(self, level: int, text: str) -> None:
        while len(self.stack) > 1:
            top = self.stack[-1]
            if top.kind == "heading" and top.depth < level:
                break
            self.stack.pop()
        node = Node("heading", level, split_math(strip_emphasis(text)))
        self.stack[-1].children.append(node)
        self.stack.append(node)
        self.current = node

    def _bullet(self, indent: int, text: str) -> None:
        depth = 100 + min(6, 1 + indent // 2)
        while len(self.stack) > 1 and self.stack[-1].depth >= depth:
            self.stack.pop()
        parent = self.stack[-1]
        segs = self._mixed(split_math(strip_emphasis(text)))

        # 一条列表项 = 一个主题；只有 --mix own 才把公式拆成独立子主题
        own = [s for s in segs if getattr(s, "as_topic", False)]
        if own:
            plain = [Seg("text", s.value) for s in segs
                     if s.type == "text" and s.value.strip() and not getattr(s, "as_topic", False)]
            if plain:
                node = Node("bullet", depth, plain)
                parent.children.append(node)
                for mseg in own:
                    node.children.append(Node("bullet", depth + 1, [Seg("math", mseg.value, mseg.display)]))
                self.current = node
                return
            # 只有公式：第一条当主体，其余作为它的子主题
            firstm, rest = own[0], own[1:]
            node = Node("bullet", depth, [Seg("math", firstm.value, firstm.display)])
            parent.children.append(node)
            for mseg in rest:
                node.children.append(Node("bullet", depth + 1, [Seg("math", mseg.value, mseg.display)]))
            self.current = node
            return

        node = Node("bullet", depth, list(segs))
        parent.children.append(node)
        self.current = node

    def _mixed(self, segs: List[Seg]) -> List[Seg]:
        """按 mix 策略调整公式位置（返回新列表，不修改入参）"""
        has_text = any(s.type == "text" and s.value.strip() for s in segs)
        has_math = any(s.type == "math" for s in segs)
        if self.mix == "keep" or not (has_text and has_math):
            return list(segs)
        text = " ".join(s.value for s in segs if s.type == "text")
        text = re.sub(r"\s+", " ", text).strip()
        out: List[Seg] = []
        for s in segs:
            if s.type == "text":
                continue
            if self.mix == "own":
                m2 = Seg("math", s.value, s.display)
                m2.as_topic = True                            # type: ignore[attr-defined]
                out.append(m2)
            else:
                out.append(s)
        if text:
            out.insert(0, Seg("text", text))
        return out

    def _normalize(self, node: Node, depth: int) -> None:
        node.depth = depth if node.kind != "heading" else max(1, node.depth)
        for child in node.children:
            self._normalize(child, node.depth + 1)


def parse(md: str, mix: str = "tail"):
    """返回 (root, title)"""
    p = Parser(mix=mix)
    root = p.parse(md)
    return root, p.title


def iter_nodes(node: Node):
    for child in node.children:
        yield child
        yield from iter_nodes(child)


def to_outline(root: Node, limit: int = 0, title: str = "") -> List[str]:
    """导出制表符缩进的纯文本大纲；limit>0 时按**节点数**上限切分。"""
    full = []
    for child in root.children:
        full.append("\t" * (child.depth - 1) + _node_text(child))
        full.extend(_walk_text(child))
    if not limit:
        return ["\n".join([title] + full) if title else "\n".join(full)]

    groups = []          # [(节点数, 行列表)]
    for child in root.children:
        block = ["\t" * (child.depth - 1) + _node_text(child)] + list(_walk_text(child))
        size = 1 + sum(1 for _ in _iter(child))
        if size > limit:                     # 单支过大：按行切
            for i in range(0, len(block), limit):
                chunk = block[i:i + limit]
                groups.append((len(chunk), chunk))
            continue
        groups.append((size, block))

    parts, cur, used = [], [], 0
    for size, block in groups:
        if cur and used + size > limit:
            parts.append(cur)
            cur, used = [], 0
        cur.extend(block)
        used += size
    if cur:
        parts.append(cur)

    out = []
    for i, part in enumerate(parts, 1):
        head = ("%s（第 %d/%d 部分）" % (title or "大纲", i, len(parts))
                if len(parts) > 1 else (title or "大纲"))
        out.append("\n".join([head] + part))
    return out


def _iter(node: Node):
    for child in node.children:
        yield child
        yield from _iter(child)


def _node_text(node: Node) -> str:
    n = 0
    out = []
    for s in node.segs:
        if s.type == "text":
            out.append(s.value)
        else:
            n += 1
            out.append("〖公式 %d〗" % n)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _walk_text(node: Node):
    for child in node.children:
        yield "\t" * (child.depth - 1) + _node_text(child)
        yield from _walk_text(child)
