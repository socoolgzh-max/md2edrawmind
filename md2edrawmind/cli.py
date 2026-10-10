# -*- coding: utf-8 -*-
"""命令行入口：md2edrawmind convert / serve / check"""
from __future__ import annotations

import argparse
import os
import sys

from . import pipeline


def cmd_convert(args) -> int:
    if not os.path.exists(args.input):
        print("[错误] 找不到文件：%s" % args.input, file=sys.stderr)
        return 2
    out = args.output or os.path.splitext(args.input)[0] + ".docx"

    def progress(msg: str, pct: int) -> None:
        bar = "█" * (pct // 5) + "·" * (20 - pct // 5)
        print("  [%s] %3d%%  %s" % (bar, pct, msg), flush=True)

    print("md2edrawmind · %s → %s" % (os.path.basename(args.input), os.path.basename(out)))
    try:
        res = pipeline.convert(args.input, out, work_dir=args.work, mix=args.mix,
                               limit=args.limit, progress=progress)
    except pipeline.PipelineError as err:
        print("\n[失败] %s" % err, file=sys.stderr)
        return 1

    print("\n完成：")
    for f in res.files:
        print("  · %s" % f)
    print("  主题 %d 个 / 公式 %d 条" % (res.nodes, res.formulas))
    if res.missing:
        print("  ⚠ 有 %d 条公式没渲染成功（已在 Word 里保留 LaTeX 原文）" % res.missing)
    if args.outline:
        for i, txt in enumerate(res.outline, 1):
            p = os.path.splitext(out)[0] + ("-大纲.txt" if len(res.outline) == 1 else "-大纲%d.txt" % i)
            open(p, "w", encoding="utf-8").write(txt)
            print("  · %s" % p)
    print("\n下一步：EdrawMind → 导入 → Word → 选择上面的 .docx")
    return 0


def cmd_serve(args) -> int:
    from .server import run_server
    return run_server(host=args.host, port=args.port, open_browser=not args.no_browser)


def cmd_check(args) -> int:
    node = pipeline.find_node()
    chrome = pipeline.find_chrome()
    ok = True
    print("环境检查")
    print("  Python : %s" % sys.version.split()[0])
    try:
        import docx  # noqa: F401
        print("  python-docx : 已安装")
    except Exception:
        print("  python-docx : 缺失  → pip install python-docx"); ok = False
    print("  Node.js : %s" % (node or "缺失  → 安装 Node 18+（渲染公式需要）"))
    ok = ok and bool(node)
    print("  浏览器  : %s" % (chrome or "缺失  → 安装 Chrome / Edge（公式转图片需要）"))
    ok = ok and bool(chrome)
    pkg = os.path.join(os.path.dirname(pipeline.tools_dir()), "node_modules", "mathjax-full")
    print("  mathjax-full : %s" % ("已安装" if os.path.isdir(pkg) else "缺失  → npm install"))
    ok = ok and os.path.isdir(pkg)
    print("\n结论：%s" % ("环境就绪 ✔" if ok else "还有缺失，先补齐上面的项 ✘"))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="md2edrawmind",
                                 description="把带 LaTeX 公式的 Markdown 转成可直接导入 EdrawMind 的 Word")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("convert", help="转换一个 Markdown 文件")
    c.add_argument("input", help="输入的 .md")
    c.add_argument("-o", "--output", help="输出的 .docx（默认与输入同名）")
    c.add_argument("--mix", choices=["tail", "own", "keep"], default="tail",
                   help="公式位置：tail=挪到主题末尾(推荐) own=公式单独成条 keep=保持原句")
    c.add_argument("--limit", type=int, default=0,
                   help="每个文件最多主题数（免费版 EdrawMind 导入上限 50，超过会自动切分）")
    c.add_argument("--work", help="中间文件目录")
    c.add_argument("--outline", action="store_true", help="同时导出纯文本大纲")
    c.set_defaults(func=cmd_convert)

    s = sub.add_parser("serve", help="启动图形界面（本地网页，无需联网）")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    s.set_defaults(func=cmd_serve)

    k = sub.add_parser("check", help="检查依赖环境")
    k.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
