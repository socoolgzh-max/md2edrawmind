# -*- coding: utf-8 -*-
"""桌面端启动器：起本地服务 -> 打开系统浏览器 -> 等待退出。

设计要点（都来自实际踩坑）：
  · 双击 exe 时没有可见控制台输出，出问题用户完全看不到原因
    -> 所有步骤写日志文件（%LOCALAPPDATA%\\md2edrawmind\\startup.log）
    -> 致命错误弹 Windows 原生对话框，而不是静默退出
  · 已经有实例在跑时，直接打开浏览器而不是又起一个服务
  · 端口被占用时自动换端口
  · 桌面端随包 Node 优先（见 md2edrawmind.paths）
"""
from __future__ import annotations

import ctypes
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser


# ------------------------------------------------------------------ 基础工具
def app_dir() -> str:
    """exe 所在目录（放日志、定位资源）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_root() -> str:
    """打包后是 PyInstaller 解包目录（_internal），开发时是仓库根目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", app_dir())
    return os.path.dirname(os.path.abspath(__file__))


def log_path() -> str:
    base = os.environ.get("LOCALAPPDATA") or app_dir()
    folder = os.path.join(base, "md2edrawmind")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = app_dir()
    return os.path.join(folder, "startup.log")


_LOG_FH = None


def log(msg: str) -> None:
    """同时写日志与标准输出（双击时后者通常不可见，保留给命令行排查）。"""
    global _LOG_FH
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        if _LOG_FH is None:
            _LOG_FH = open(log_path(), "a", encoding="utf-8")
            _LOG_FH.write("\n==== md2edrawmind 启动 %s ====\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        _LOG_FH.write(line + "\n")
        _LOG_FH.flush()
    except Exception:
        pass


def alert(title: str, text: str) -> None:
    """Windows 原生弹窗，保证双击启动时用户能看到失败原因。"""
    log("弹窗: %s | %s" % (title, text.replace("\n", " / ")))
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)  # MB_ICONINFORMATION
    except Exception:
        pass


def alert_error(title: str, text: str) -> None:
    log("错误弹窗: %s | %s" % (title, text.replace("\n", " / ")))
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def wire_env() -> str:
    """把随包资源位置告诉 md2edrawmind.paths。"""
    root = resource_root()
    for key, name in (("MD2EDRAW_WEB", "web"),
                      ("MD2EDRAW_TOOLS", "tools"),
                      ("MD2EDRAW_NODE_MODULES", "node_modules")):
        path = os.path.join(root, name)
        if os.path.isdir(path):
            os.environ[key] = path
            log("资源 %s = %s" % (key, path))
        else:
            log("缺少资源 %s（预期 %s）" % (key, path))
    node = os.path.join(root, "node", "node.exe")
    if os.path.isfile(node):
        os.environ["MD2EDRAW_NODE"] = node
        log("随包 Node = %s" % node)
    else:
        log("未找到随包 Node（预期 %s），回退到系统 Node" % node)
    return root


def free_port(preferred: int = 8787) -> int:
    for port in (preferred, 8788, 8789, 8790, 8799, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
        except OSError:
            continue
    return 0


def already_running() -> int:
    """已有实例在跑就复用，避免重复开一堆服务。"""
    for port in (8787, 8788, 8789, 8790, 8799):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                return port
        except OSError:
            continue
    return 0


# ------------------------------------------------------------------ 主流程
def run() -> int:
    log("=" * 56)
    log("md2edrawmind 桌面端启动")
    log("exe 目录: %s" % app_dir())
    log("资源根: %s" % resource_root())
    log("Python: %s" % sys.version.replace("\n", " "))

    running = already_running()
    if running:
        url = "http://127.0.0.1:%d/" % running
        log("已有实例在运行，直接打开 %s" % url)
        webbrowser.open(url)
        return 0

    wire_env()

    from md2edrawmind import pipeline
    from md2edrawmind.server import run_server

    node = pipeline.find_node()
    chrome = pipeline.find_chrome()
    log("Node   : %s" % (node or "未找到"))
    log("浏览器 : %s" % (chrome or "未找到"))
    if not node:
        alert_error("缺少 Node 运行时",
                    "随包的 Node 没找到，公式无法渲染。\n\n"
                    "请重新解压整个文件夹（不要只把 exe 复制出来）。")
    if not chrome:
        alert_error("找不到浏览器",
                    "公式转图片需要 Chrome 或 Edge。\n\n请先安装其中一个再运行本程序。")

    port = free_port(int(os.environ.get("MD2EDRAW_PORT", "8787")))
    if not port:
        alert_error("端口被占用", "8787-8799 都被占用了，请关掉占用端口的程序后重试。")
        return 1
    url = "http://127.0.0.1:%d/" % port
    log("监听端口: %d" % port)

    def open_later() -> None:
        # 等端口真的可连再开浏览器，避免打开空白页
        for _ in range(80):
            time.sleep(0.25)
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                    break
            except OSError:
                continue
        log("打开浏览器: %s" % url)
        try:
            opened = webbrowser.open(url)
            log("webbrowser.open 返回 %s" % opened)
            if not opened:
                alert("md2edrawmind 已启动",
                      "请手动在浏览器打开：\n\n%s\n\n（关掉黑色命令行窗口即停止服务）" % url)
        except Exception as exc:
            log("打开浏览器失败: %r" % exc)
            alert("md2edrawmind 已启动",
                  "自动打开浏览器失败。\n请手动访问：\n\n%s" % url)

    threading.Thread(target=open_later, daemon=True).start()
    log("启动 HTTP 服务 ...")
    try:
        run_server(host="127.0.0.1", port=port, open_browser=False)
    except KeyboardInterrupt:
        log("收到中断，退出")
    except Exception:
        tb = traceback.format_exc()
        log("服务异常:\n%s" % tb)
        alert_error("启动失败", "服务启动时出错：\n\n%s\n\n完整日志：\n%s" % (tb[-500:], log_path()))
        return 1
    return 0


def main() -> int:
    try:
        return run()
    except Exception:
        tb = traceback.format_exc()
        try:
            log("致命错误:\n%s" % tb)
        except Exception:
            pass
        alert_error("md2edrawmind 启动失败",
                    "程序启动时出错。\n\n%s\n\n完整日志：\n%s" % (tb[-500:], log_path()))
        return 1


if __name__ == "__main__":
    sys.exit(main())
