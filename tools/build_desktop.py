# -*- coding: utf-8 -*-
"""打包桌面端（PyInstaller）。

产物：dist/md2edrawmind/md2edrawmind.exe —— 双击即用，用户无需安装 Python / Node。
公式渲染所需的 Node 运行时与 mathjax-full / pngjs 一并随包分发。
浏览器（Chrome / Edge）仍使用系统已安装的，用于把公式渲染成图片。

用法:
  python tools/build_desktop.py            # 打包（onedir）
  python tools/build_desktop.py --zip      # 打包并压缩为 GitHub Release 用的 zip
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "build", "desktop-stage")
DIST = os.path.join(ROOT, "dist")
APP_NAME = "md2edrawmind"

# mathjax-full 里用不到的部分（es5 是给老浏览器的打包产物，ts 是源码）
MATHJAX_SKIP = {"es5", "ts"}
NODE_CANDIDATES = [
    r"D:\Envirment\nvm\nodejs\node.exe",
    r"C:\Program Files\nodejs\node.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs\node.exe"),
]


def find_node() -> str:
    for c in NODE_CANDIDATES:
        if os.path.exists(c):
            return c
    exe = shutil.which("node")
    if exe:
        return exe
    raise SystemExit("找不到 node.exe，无法随包分发 Node 运行时")


def resolve_packages(root_pkgs=("mathjax-full", "pngjs")) -> list:
    """递归解析运行时依赖，避免漏掉传递依赖。

    踩过的坑：最初只拷 mathjax-full 与 pngjs，漏了它依赖的 mhchemparser，
    于是打包版渲染公式时 require 失败（开发机上根 node_modules 里本来就有，
    所以完全看不出来），表现是转换卡在 25% 然后报「出错了」。
    """
    nm = os.path.join(ROOT, "node_modules")
    seen, queue = set(), list(root_pkgs)
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        pkg_json = os.path.join(nm, name, "package.json")
        if not os.path.isfile(pkg_json):
            print("    [警告] 依赖缺失: %s" % name)
            continue
        seen.add(name)
        try:
            with open(pkg_json, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception:
            meta = {}
        for dep in (meta.get("dependencies") or {}):
            if dep not in seen:
                queue.append(dep)
    return sorted(seen)


def copy_tree(src: str, dst: str, skip_dirs=()):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
    for name in skip_dirs:
        p = os.path.join(dst, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)


def stage() -> str:
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE, exist_ok=True)

    print("[stage] web/ 与 tools/")
    copy_tree(os.path.join(ROOT, "web"), os.path.join(STAGE, "web"))
    copy_tree(os.path.join(ROOT, "tools"), os.path.join(STAGE, "tools"),
              skip_dirs=("__pycache__",))

    pkgs = resolve_packages()
    print("[stage] node_modules：%d 个包" % len(pkgs))
    print("        " + ", ".join(pkgs))
    nm_src = os.path.join(ROOT, "node_modules")
    nm_dst = os.path.join(STAGE, "node_modules")
    for pkg in pkgs:
        src = os.path.join(nm_src, pkg)
        if not os.path.isdir(src):
            raise SystemExit("缺少依赖 %s，请先 npm install" % pkg)
        # mathjax-full 的 es5（老浏览器打包产物）与 ts（源码）运行时用不到
        skip = MATHJAX_SKIP if pkg == "mathjax-full" else ()
        copy_tree(src, os.path.join(nm_dst, pkg), skip_dirs=skip)

    print("[stage] Node 运行时")
    node_dst_dir = os.path.join(STAGE, "node")
    os.makedirs(node_dst_dir, exist_ok=True)
    shutil.copy2(find_node(), os.path.join(node_dst_dir, "node.exe"))

    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(STAGE) for f in fs)
    print("[stage] 资源合计 %.1f MB" % (size / 1048576.0))
    return STAGE


def build() -> str:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", APP_NAME,
        # --windowed：PE 子系统设为 GUI，双击不弹黑色命令行窗口。
        # 代价是 sys.stdout/stderr 变成 None，所以 desktop_launcher 必须把诊断
        # 写进 startup.log 并用原生对话框报错，不能依赖控制台输出。
        "--windowed",
        "--paths", ROOT,
        "--add-data", "%s%s." % (STAGE, os.pathsep),
        "--hidden-import", "md2edrawmind.server",
        "--hidden-import", "md2edrawmind.pipeline",
        # 桌面窗口：pywebview 在 Windows 上用 WebView2，依赖 pythonnet/clr_loader，
        # 这些包的 DLL 与数据文件必须显式收集，否则打包后窗口起不来。
        "--collect-all", "webview",
        "--collect-all", "clr_loader",
        "--collect-all", "pythonnet",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "PyQt5",
        os.path.join(ROOT, "desktop_launcher.py"),
    ]
    print("[build] " + " ".join(cmd[:3]) + " ...")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("PyInstaller 打包失败")
    exe = os.path.join(DIST, APP_NAME, APP_NAME + ".exe")
    if not os.path.exists(exe):
        raise SystemExit("未生成 %s" % exe)
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(os.path.join(DIST, APP_NAME)) for f in fs)
    print("[build] 完成 %s  (%.1f MB)" % (exe, size / 1048576.0))
    return exe


def make_zip() -> str:
    folder = os.path.join(DIST, APP_NAME)
    out = os.path.join(DIST, "%s-windows-x64.zip" % APP_NAME)
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dp, _, fs in os.walk(folder):
            for f in fs:
                full = os.path.join(dp, f)
                z.write(full, os.path.relpath(full, DIST))
    print("[zip] %s  (%.1f MB)" % (out, os.path.getsize(out) / 1048576.0))
    return out


def main() -> int:
    stage()
    build()
    if "--zip" in sys.argv:
        make_zip()
    return 0


if __name__ == "__main__":
    sys.exit(main())
