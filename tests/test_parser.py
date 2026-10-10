# -*- coding: utf-8 -*-
"""解析器与 Word 生成器的单元测试（不需要浏览器/网络）。

用法: python tests/test_parser.py
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from _utf8 import ensure_utf8                                  # noqa: E402
from md2edrawmind import parser as P                           # noqa: E402
from md2edrawmind.docx_writer import DocxBuilder, count_nodes   # noqa: E402

ensure_utf8()

FAILED = []


def check(name, cond, detail=""):
    print("  %s %s%s" % ("✔" if cond else "✘", name, ("  → " + detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def test_parse_basic():
    print("解析：层级与公式")
    md = "# 标题\n\n## 一、章\n\n- 甲\n  - 乙 $a^2$\n- 丙：$x=1$，$y=2$\n"
    root, title = P.parse(md, mix="keep")
    nodes = list(P.iter_nodes(root))
    check("标题提取", title == "标题", title)
    check("主题数 = 标题 + 章 + 4 个条目", len(nodes) == 5, str(len(nodes)))
    check("层级：章=1", nodes[0].depth == 1, str(nodes[0].depth))
    check("层级：乙=3", nodes[2].depth == 3, str(nodes[2].depth))
    check("公式识别（keep 保持原句）",
          [n.math for n in nodes if n.math] == [["a^2"], ["x=1", "y=2"]],
          str([n.math for n in nodes]))


def test_mix_tail():
    print("解析：--mix tail（文字在前，公式挪到末尾）")
    md = "- 若 $\\sum u_n$ 收敛，则 $\\lim u_n = 0$\n"
    root, _ = P.parse(md, mix="tail")
    node = root.children[0]
    kinds = [s.type for s in node.segs]
    check("文字在前", kinds[0] == "text", str(kinds))
    check("公式在后", kinds[-1] == "math", str(kinds))
    check("公式数 = 2", len(node.math) == 2, str(node.math))
    check("文字合并成一句", "收敛" in node.text and "若" in node.text, node.text)


def test_mix_own():
    print("解析：--mix own（公式独立成条）")
    md = "- 计算 $L = \\lim \\frac{u_n}{v_n}$ 的值\n"
    root, _ = P.parse(md, mix="own")
    node = root.children[0]
    check("说明文字成为主题", bool(node.text), repr(node.text))
    check("公式成为它的子主题", len(node.children) == 1 and bool(node.children[0].math),
          str([c.math for c in node.children]))


def test_outline():
    print("导出：纯文本大纲")
    md = "# T\n\n## 一\n\n" + "\n".join("- 项 %d" % i for i in range(8))
    root, title = P.parse(md, mix="tail")
    one = P.to_outline(root, limit=0, title=title)
    check("单份大纲", len(one) == 1)
    check("含制表符缩进", "\t" in one[0], repr(one[0]))
    parts = P.to_outline(root, limit=3, title=title)
    check("按上限切分", len(parts) >= 2, str(len(parts)))


def test_docx(tmp_dir="build"):
    print("生成：docx 层级")
    os.makedirs(tmp_dir, exist_ok=True)
    md = "# T\n\n## 一\n\n- 甲\n  - 乙\n"
    root, title = P.parse(md, mix="tail")
    out = os.path.join(tmp_dir, "unit.docx")
    builder = DocxBuilder({}, title)
    builder.build(root, out)
    doc = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    levels = re.findall(r'w:outlineLvl w:val="(\d+)"', doc)
    # 标题段 + 章 + 甲 + 乙
    check("写了 outlineLvl 且层级递增", levels == ["0", "1", "2", "2"], str(levels))
    check("无公式时不报缺图", not builder.missing, str(builder.missing))


def test_split():
    print("切分：按主题上限")
    md = "# T\n\n## A\n\n" + "\n".join("- 项 %d" % i for i in range(12))
    root, _ = P.parse(md, mix="tail")
    total = sum(count_nodes(c) for c in root.children)
    for limit in (3, 4, 5, 7):
        parts = DocxBuilder.split(root, limit)
        sizes = [sum(count_nodes(n) for n in nodes) for _prefix, nodes in parts]
        check("limit=%d：每份不超上限" % limit, all(s <= limit for s in sizes), str(sizes))
        check("limit=%d：全部覆盖" % limit, sum(sizes) == total, "%s vs %s" % (sizes, total))


def main():
    for fn in (test_parse_basic, test_mix_tail, test_mix_own, test_outline, test_docx, test_split):
        fn()
        print()
    if FAILED:
        print("失败 %d 项：%s" % (len(FAILED), ", ".join(FAILED)))
        return 1
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
