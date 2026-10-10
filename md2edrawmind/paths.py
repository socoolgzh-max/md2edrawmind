# -*- coding: utf-8 -*-
"""资源位置解析，支持三种部署形态：

1. 桌面端   PyInstaller 解包目录，由 desktop_launcher.py 设置 MD2EDRAW_* 环境变量
2. 源码仓库  <root>/{web,tools,node_modules}
3. pip 安装  site-packages/md2edrawmind/{web,tools}

环境变量永远优先：桌面端必须用随包的资源，不能因为开发机上也有
web/ 和 tools/ 就被带偏。
"""
from __future__ import annotations

import os

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(PKG_DIR)


def _first_dir(*cands):
    for c in cands:
        if c and os.path.isdir(c):
            return c
    return None


def web_dir() -> str:
    """静态资源目录（含 index.html 的那个）"""
    env = os.environ.get("MD2EDRAW_WEB")
    if env and os.path.isfile(os.path.join(env, "index.html")):
        return env
    repo_web = os.path.join(REPO_ROOT, "web")
    if os.path.isfile(os.path.join(repo_web, "index.html")):
        return repo_web
    return _first_dir(os.path.join(PKG_DIR, "web"), repo_web) or os.path.join(PKG_DIR, "web")


def tools_dir() -> str:
    """tools/*.js 所在目录（render.js / mathjax.js）"""
    env = os.environ.get("MD2EDRAW_TOOLS")
    if env and os.path.isfile(os.path.join(env, "render.js")):
        return env
    repo_tools = os.path.join(REPO_ROOT, "tools")
    if os.path.isfile(os.path.join(repo_tools, "render.js")):
        return repo_tools
    return _first_dir(env, os.path.join(PKG_DIR, "tools"), repo_tools) or os.path.join(PKG_DIR, "tools")


def node_modules_dir() -> str:
    """mathjax-full / pngjs 的 node_modules 目录"""
    return _first_dir(os.environ.get("MD2EDRAW_NODE_MODULES"),
                      os.path.join(tools_dir(), "node_modules"),
                      os.path.join(REPO_ROOT, "node_modules"),
                      os.path.join(PKG_DIR, "node_modules")) or os.path.join(REPO_ROOT, "node_modules")


def bundled_node() -> str | None:
    """桌面端随包的 Node 运行时（优先使用，用户机器上无需装 Node）"""
    p = os.environ.get("MD2EDRAW_NODE")
    return p if p and os.path.isfile(p) else None


def has_node_deps() -> bool:
    """mathjax-full 是否可用"""
    cands = [os.environ.get("MD2EDRAW_NODE_MODULES"),
             os.path.join(tools_dir(), "node_modules"),
             os.path.join(REPO_ROOT, "node_modules"),
             os.path.join(PKG_DIR, "node_modules")]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "mathjax-full")):
            return True
    return False
