# -*- coding: utf-8 -*-
"""构建 Windows 安装器（Inno Setup）。

前置：先跑 tools/build_desktop.py 生成 dist\\md2edrawmind\\。

用法:
  python tools/build_installer.py            # 打包 + 编译安装器
  python tools/build_installer.py --no-build # 只编译安装器（复用已有 dist）
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "dist", "md2edrawmind")
ISS = os.path.join(ROOT, "tools", "installer.iss")
SETUP = os.path.join(ROOT, "dist", "md2edrawmind-1.0.0-setup.exe")

ISCC_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def find_iscc() -> str:
    for c in ISCC_CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("找不到 ISCC.exe（Inno Setup）。安装：winget install JRSoftware.InnoSetup")


def main() -> int:
    if "--no-build" not in sys.argv:
        print("[1/3] PyInstaller 打包")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_desktop.py")], cwd=ROOT)
        if r.returncode != 0:
            raise SystemExit("桌面端打包失败")

    if not os.path.isdir(STAGE):
        raise SystemExit("缺少 %s，请先跑 tools/build_desktop.py" % STAGE)

    print("[2/3] 图标与安装说明")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_icon.py")], cwd=ROOT)

    print("[3/3] 编译安装器")
    iscc = find_iscc()
    cmd = [iscc, "/DStageDir=%s" % STAGE, ISS]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout or "").strip().splitlines()[-6:]
    for line in tail:
        print("   " + line)
    if r.returncode != 0:
        print((r.stderr or "")[-800:])
        raise SystemExit("Inno Setup 编译失败")
    if not os.path.exists(SETUP):
        raise SystemExit("未生成 %s" % SETUP)
    print("[done] %s  (%.1f MB)" % (SETUP, os.path.getsize(SETUP) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
