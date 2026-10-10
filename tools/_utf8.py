# -*- coding: utf-8 -*-
"""控制台编码兜底：Windows 上 stdout 可能是 cp1252/GBK，打印 ✔ 之类字符会抛
UnicodeEncodeError。所有脚本启动时调用一次 ensure_utf8()。

放在 tools/ 下是为了让 tests/ 也能用，而不需要导入整个 md2edrawmind 包
（避免测试环境被迫安装 Pillow 等依赖）。
"""
from __future__ import annotations

import sys


def ensure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
        except Exception:
            pass


if __name__ == "__main__":
    ensure_utf8()
    print("控制台已切换为 UTF-8 ✔")
