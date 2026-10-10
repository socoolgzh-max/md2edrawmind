# -*- coding: utf-8 -*-
"""校验 README 里的锚点链接与相对链接是否都能解析。

用法: python tools/check_readme_links.py
"""
import os
import re
import sys
import unicodedata

try:  # Windows 控制台可能是 GBK，输出 ✔ 会崩
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slug(text: str) -> str:
    """近似 GitHub 的标题锚点规则：小写、去标点、空格换连字符；中文保留"""
    t = text.strip().lower()
    t = re.sub(r"`|\*|\[|\]|\(|\)|、|，|。|：|！|？|【|】", "", t)
    t = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t)
    return t


def anchors(md: str):
    out = set()
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", md, re.M):
        out.add(slug(m.group(1)))
    return out


def main() -> int:
    bad = []
    for name in ("README.md", "README.zh-CN.md"):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            print("缺少", name)
            return 1
        md = open(path, encoding="utf-8").read()
        anch = anchors(md)
        for m in re.finditer(r"\]\((#[^)]+)\)", md):
            target = m.group(1)[1:]
            if target not in anch:
                bad.append((name, "#" + target))
        for m in re.finditer(r"\]\((?!https?:|#)([^)]+?)\)", md):
            rel = m.group(1).split("#")[0]
            if rel and not os.path.exists(os.path.join(ROOT, rel)):
                bad.append((name, rel))
        print("%-16s 标题锚点 %d 个，检查完成" % (name, len(anch)))
    if bad:
        print("\n无效链接：")
        for f, t in bad:
            print("  %s -> %s" % (f, t))
        return 1
    print("\n全部链接有效 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
