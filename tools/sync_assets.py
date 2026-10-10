# -*- coding: utf-8 -*-
"""打包前把根目录的 web/ 与 tools/ 镜像进包内（md2edrawmind/），
这样 wheel / sdist 才能带上静态资源与渲染脚本。

用法: python tools/sync_assets.py
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "md2edrawmind")

PAIRS = [("web", ("*.html", "*.css", "*.js")),
         ("tools", ("*.js",))]

SKIP = {"node_modules", "__pycache__"}


def main():
    n = 0
    for sub, patterns in PAIRS:
        src = os.path.join(ROOT, sub)
        dst = os.path.join(PKG, sub)
        if not os.path.isdir(src):
            print("跳过（源目录不存在）:", src)
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in SKIP]
            rel = os.path.relpath(root, src)
            target = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(target, exist_ok=True)
            for f in files:
                if any(f.endswith(p.lstrip("*")) for p in patterns):
                    shutil.copy2(os.path.join(root, f), os.path.join(target, f))
                    n += 1
    print("已镜像 %d 个资源文件到 md2edrawmind/" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
