# -*- coding: utf-8 -*-
"""桌面端启动器：起本地服务 -> 打开系统浏览器 -> 等待退出。

作为 PyInstaller 的入口点。冻结后所有资源位于 sys._MEIPASS 下，
由 md2edrawmind.paths 通过环境变量 MD2EDRAW_WEB / MD2EDRAW_TOOLS /
MD2EDRAW_NODE_MODULES / MD2EDRAW_NODE 解析。
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser


def resource_root() -> str:
    """打包后是解包目录，开发时是仓库根目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def wire_env() -> str:
    """把随包资源位置告诉 paths 模块，返回资源根目录。"""
    root = resource_root()
    pairs = {
        "MD2EDRAW_WEB": os.path.join(root, "web"),
        "MD2EDRAW_TOOLS": os.path.join(root, "tools"),
        "MD2EDRAW_NODE_MODULES": os.path.join(root, "node_modules"),
    }
    for key, path in pairs.items():
        if os.path.isdir(path):
            os.environ[key] = path
    node = os.path.join(root, "node", "node.exe")
    if os.path.isfile(node):
        os.environ["MD2EDRAW_NODE"] = node
    return root


def free_port(preferred: int = 8787) -> int:
    for port in [preferred, 8788, 8790, 8799, 0]:
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1] if port else 0
        except OSError:
            continue
    return 0


def main() -> int:
    root = wire_env()

    from md2edrawmind import pipeline
    from md2edrawmind.server import run_server

    print("=" * 58)
    print("  md2edrawmind · 公式笔记 → 思维导图")
    print("=" * 58)
    node = pipeline.find_node()
    chrome = pipeline.find_chrome()
    print("  Node   : %s" % (node or "未找到"))
    print("  浏览器 : %s" % (chrome or "未找到"))
    if not node:
        print("\n  [警告] 缺少 Node 运行时，公式将无法渲染。")
    if not chrome:
        print("\n  [警告] 缺少 Chrome / Edge，公式无法转成图片。")
    print("  资源   : %s" % root)
    print()

    port = free_port(int(os.environ.get("MD2EDRAW_PORT", "8787")))
    url = "http://127.0.0.1:%d/" % port

    def open_later() -> None:
        time.sleep(1.0)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        print("  已在浏览器打开：%s" % url)
        print("  （如果没有自动打开，请手动复制上面的地址）")

    threading.Thread(target=open_later, daemon=True).start()
    print("  关闭这个窗口即停止服务。\n")

    try:
        run_server(host="127.0.0.1", port=port, open_browser=False)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
