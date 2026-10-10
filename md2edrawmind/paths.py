# -*- coding: utf-8 -*-
"""资源位置解析：同时支持「源码仓库布局」和「pip 安装后布局」。

源码仓库:
    <root>/md2edrawmind/{cli,parser,...}.py
    <root>/web/*
    <root>/tools/*.js
    <root>/node_modules/mathjax-full

pip 安装:
    site-packages/md2edrawmind/{cli,parser,...}.py
    site-packages/md2edrawmind/web/*
    site-packages/md2edrawmind/tools/*.js
    （node_modules 需由用户在任意位置 npm install mathjax-full，或设置
      MD2EDRAW_TOOLS 环境变量指向已安装好依赖的 tools 目录）
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
    """静态资源目录。

    源码仓库布局下必须优先用仓库根的 web/（开发时就在那里改），
    否则会一直读到 tools/sync_assets.py 生成的包内镜像副本。
    pip 安装后 REPO_ROOT/web 不存在，自然回退到包内的 web/。
    """
    repo_web = os.path.join(REPO_ROOT, "web")
    if os.path.isfile(os.path.join(repo_web, "index.html")):
        return repo_web
    return _first_dir(os.path.join(PKG_DIR, "web"), repo_web) or os.path.join(PKG_DIR, "web")


def tools_dir() -> str:
    """tools/*.js 所在目录（render.js / mathjax.js）"""
    env = os.environ.get("MD2EDRAW_TOOLS")
    repo_tools = os.path.join(REPO_ROOT, "tools")
    if os.path.isfile(os.path.join(repo_tools, "render.js")):
        return repo_tools
    return _first_dir(env, os.path.join(PKG_DIR, "tools"), repo_tools) or os.path.join(PKG_DIR, "tools")


def node_modules_dir() -> str:
    """mathjax-full / pngjs 的 node_modules 目录"""
    env = os.environ.get("MD2EDRAW_NODE_MODULES")
    return _first_dir(env,
                      os.path.join(tools_dir(), "node_modules"),
                      os.path.join(REPO_ROOT, "node_modules"),
                      os.path.join(PKG_DIR, "node_modules")) or os.path.join(REPO_ROOT, "node_modules")


def has_node_deps() -> bool:
    """mathjax-full / pngjs 是否可用（检查所有候选 node_modules）"""
    cands = [os.environ.get("MD2EDRAW_NODE_MODULES"),
             os.path.join(tools_dir(), "node_modules"),
             os.path.join(REPO_ROOT, "node_modules"),
             os.path.join(PKG_DIR, "node_modules")]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "mathjax-full")):
            return True
    return False
