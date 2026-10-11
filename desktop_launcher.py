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

# 打包为 GUI 子系统（--windowed）后，sys.stdout / sys.stderr 是 None。
# 有些库或第三方扩展直接写它们会抛异常，这里统一指向空设备兜底。
# 所有诊断信息仍然会写进 startup.log，不依赖控制台。
if getattr(sys, "frozen", False):
    try:
        _devnull = open(os.devnull, "w", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = _devnull
        if sys.stderr is None:
            sys.stderr = _devnull
    except Exception:
        pass


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
def fetch_result(port: int, job: str, index: int = 0):
    """从本地服务取回转换结果（文件名 + 字节）。"""
    import urllib.request

    url = "http://127.0.0.1:%d/api/download/%s/%d" % (port, job, index)
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
        disp = resp.headers.get("Content-Disposition", "")
    name = "output.docx"
    if "filename*=UTF-8''" in disp:
        from urllib.parse import unquote

        name = unquote(disp.split("filename*=UTF-8''", 1)[1].strip().strip('"'))
    return name, data


class DesktopApi:
    """暴露给页面的 JS 桥。

    为什么需要它：pywebview 的 WebView2 后端把下载开关写死在 settings
    (ALLOW_DOWNLOADS=False) 里，且 settings 是不可变字典、start() 也不收这个参数，
    结果页面里点 <a href=...> 下载会被静默取消（用户看到"点了没反应"）。
    所以桌面端绕开 WebView2 的下载机制，直接用原生「另存为」对话框落盘。
    """

    def __init__(self, port: int, window_holder: dict):
        self.port = port
        self.holder = window_holder

    def save_file(self, name: str, job: str, index: int = 0) -> dict:
        import webview

        window = self.holder.get("window")
        if window is None:
            return {"ok": False, "error": "窗口未就绪"}
        try:
            real_name, data = fetch_result(self.port, job, int(index))
        except Exception as exc:
            log("取回结果失败: %r" % exc)
            return {"ok": False, "error": "取回文件失败：%s" % exc}

        ext = os.path.splitext(real_name)[1] or ".docx"
        dialog_type = webview.FileDialog.SAVE if hasattr(webview, "FileDialog") else 30
        try:
            target = window.create_file_dialog(
                dialog_type,
                save_filename=real_name,
                file_types=("Word 文档 (*.docx)", "文本大纲 (*.txt)", "所有文件 (*.*)"),
            )
        except Exception as exc:
            log("保存对话框失败: %r" % exc)
            return {"ok": False, "error": "打开保存对话框失败：%s" % exc}
        if not target:
            log("用户取消了保存")
            return {"ok": False, "cancelled": True}

        path = target[0] if isinstance(target, (list, tuple)) else target
        if not os.path.splitext(path)[1]:
            path += ext
        try:
            with open(path, "wb") as fh:
                fh.write(data)
            log("已保存结果: %s (%.1f KB)" % (path, len(data) / 1024))
            return {"ok": True, "path": path, "size": len(data)}
        except Exception as exc:
            log("写文件失败: %r" % exc)
            return {"ok": False, "error": "写入失败：%s" % exc}


def open_native_window(url: str, port: int) -> bool:
    """用一个真正的桌面窗口打开界面（WebView2）。失败则回退到浏览器。

    用 pywebview 包一层，界面代码完全复用；用户看到的是独立窗口和任务栏图标，
    而不是浏览器标签页。
    """
    try:
        import webview
    except Exception as exc:
        log("pywebview 不可用（%r），回退到浏览器" % exc)
        return False

    # 等端口真的可连，避免窗口里出现空白页
    for _ in range(80):
        time.sleep(0.25)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                break
        except OSError:
            continue

    holder: dict = {}
    try:
        log("创建桌面窗口: %s" % url)
        window = webview.create_window(
            "md2edrawmind · 公式笔记 → 思维导图",
            url,
            js_api=DesktopApi(port, holder),
            width=1080,
            height=820,
            min_size=(420, 560),
            text_select=True,
        )
        holder["window"] = window
        # gui=None 让 pywebview 自己挑（Windows 上就是 WebView2 / EdgeChromium）
        webview.start(private_mode=False)
        log("窗口已关闭")
        return True
    except Exception as exc:
        log("创建窗口失败: %r" % exc)
        return False


def run() -> int:
    log("=" * 56)
    log("md2edrawmind 桌面端启动")
    log("exe 目录: %s" % app_dir())
    log("资源根: %s" % resource_root())
    log("Python: %s" % sys.version.replace("\n", " "))

    running = already_running()
    if running:
        url = "http://127.0.0.1:%d/" % running
        log("已有实例在运行，直接打开窗口 %s" % url)
        if not open_native_window(url, running):
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

    # 先在后台线程里跑 HTTP 服务，主线程留给桌面窗口（WebView 必须跑在主线程）
    def serve() -> None:
        try:
            run_server(host="127.0.0.1", port=port, open_browser=False)
        except Exception:
            log("服务异常:\n%s" % traceback.format_exc())

    threading.Thread(target=serve, daemon=True).start()
    log("HTTP 服务已在线程中启动")

    if os.environ.get("MD2EDRAW_USE_BROWSER") == "1":
        log("按环境变量要求改用系统浏览器")
        webbrowser.open(url)
        while True:
            time.sleep(3600)
        return 0

    if open_native_window(url, port):
        return 0

    # 窗口起不来（缺 WebView2 等）就退回浏览器，至少能用
    alert("md2edrawmind 已启动",
          "没能创建桌面窗口，已在浏览器里打开界面：\n\n%s\n\n"
          "（如果浏览器也没打开，请手动复制上面的地址）" % url)
    try:
        webbrowser.open(url)
    except Exception as exc:
        log("打开浏览器失败: %r" % exc)
    while True:
        time.sleep(3600)
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
