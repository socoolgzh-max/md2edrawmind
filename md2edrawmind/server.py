# -*- coding: utf-8 -*-
"""本地 GUI：标准库 http.server，负责上传、转换进度（SSE）、下载。零额外依赖。"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import pipeline


def parse_multipart(body: bytes, content_type: str):
    """极简 multipart/form-data 解析（Python 3.13 已移除 cgi 模块）。

    返回 {字段名: {"filename": str|None, "data": bytes}}
    """
    m = re.search(r'boundary="?([^";]+)"?', content_type or "")
    if not m:
        return {}
    boundary = ("--" + m.group(1)).encode()
    out = {}
    for chunk in body.split(boundary):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk == b"--":
            continue
        head, _, data = chunk.partition(b"\r\n\r\n")
        if not _:
            continue
        text = head.decode("utf-8", "replace")
        nm = re.search(r'name="([^"]*)"', text)
        if not nm:
            continue
        fn = re.search(r'filename="([^"]*)"', text)
        out[nm.group(1)] = {
            "filename": fn.group(1) if fn else None,
            "data": data.rstrip(b"\r\n"),
        }
    return out

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

# 任务表：id -> {status, pct, log[], files[], error}
JOBS = {}
JOBS_LOCK = threading.Lock()


def _job(job_id):
    with JOBS_LOCK:
        return JOBS.get(job_id)


def _update(job_id, **kw):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job.update(kw)


def _push_log(job_id, msg):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job["log"].append(msg)


def _run_job(job_id, md_path, out_path, work_dir, mix, limit):
    try:
        def progress(msg, pct):
            _update(job_id, pct=pct, message=msg)
            _push_log(job_id, msg)

        res = pipeline.convert(md_path, out_path, work_dir=work_dir, mix=mix,
                               limit=limit, progress=progress)
        _update(job_id, status="done", pct=100, message="完成",
                files=[{"path": f, "name": os.path.basename(f), "size": os.path.getsize(f)}
                       for f in res.files],
                nodes=res.nodes, formulas=res.formulas, missing=res.missing)
    except Exception as err:                       # noqa: BLE001
        _update(job_id, status="error", message=str(err), error=str(err))


class Handler(BaseHTTPRequestHandler):
    server_version = "md2edrawmind"

    # ---------------- 工具 ----------------
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):            # 静音
        pass

    # ---------------- GET ----------------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        if path == "/api/env":
            return self._json({
                "node": pipeline.find_node(),
                "chrome": pipeline.find_chrome(),
                "version": "1.0.0",
            })
        m = re.match(r"^/api/progress/([\w-]+)$", path)
        if m:
            return self._sse(m.group(1))
        m = re.match(r"^/api/download/([\w-]+)/(\d+)$", path)
        if m:
            return self._download(m.group(1), int(m.group(2)))
        if path.startswith("/static/"):
            name = os.path.basename(path)
            ctype = "text/css" if name.endswith(".css") else "application/javascript"
            return self._static(name, ctype + "; charset=utf-8")
        self._send(404, b"not found", "text/plain")

    def _static(self, name, ctype):
        p = os.path.join(WEB_DIR, name)
        if not os.path.exists(p):
            return self._send(404, b"missing asset", "text/plain")
        self._send(200, open(p, "rb").read(), ctype)

    def _sse(self, job_id):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        import time
        last = None
        while True:
            job = _job(job_id)
            if job is None:
                self.wfile.write(b"event: error\ndata: {}\n\n")
                self.wfile.flush()
                return
            payload = json.dumps({k: job[k] for k in
                                  ("status", "pct", "message", "files", "error", "nodes", "formulas", "missing")
                                  if k in job}, ensure_ascii=False)
            if payload != last:
                self.wfile.write(("data: %s\n\n" % payload).encode("utf-8"))
                self.wfile.flush()
                last = payload
            if job.get("status") in ("done", "error"):
                self.wfile.write(b"event: end\ndata: {}\n\n")
                self.wfile.flush()
                return
            time.sleep(0.4)

    def _download(self, job_id, index):
        job = _job(job_id)
        if not job or not job.get("files") or index >= len(job["files"]):
            return self._send(404, b"not found", "text/plain")
        f = job["files"][index]
        data = open(f["path"], "rb").read()
        name = f["name"].encode("utf-8").decode("latin-1", "ignore")
        self._send(200, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                   {"Content-Disposition": "attachment; filename*=UTF-8''%s" % _url_quote(f["name"])})

    # ---------------- POST ----------------
    def do_POST(self):
        path = self.path.split("?")[0]
        if path != "/api/upload":
            return self._json({"error": "unknown endpoint"}, 404)

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 64 * 1024 * 1024:
            return self._json({"error": "请求体为空或过大（上限 64MB）"}, 400)
        body = self.rfile.read(length)
        form = parse_multipart(body, self.headers.get("Content-Type", ""))
        if "file" not in form or not form["file"]["data"]:
            return self._json({"error": "没有收到文件"}, 400)

        item = form["file"]
        data = item["data"]
        filename = item["filename"] or "input.md"

        def field(name, default=""):
            v = form.get(name)
            return v["data"].decode("utf-8", "replace") if v else default

        mix = field("mix", "tail").strip()
        if mix not in ("tail", "own", "keep"):
            mix = "tail"
        try:
            limit = int(field("limit", "0") or 0)
        except ValueError:
            limit = 0

        job_id = uuid.uuid4().hex[:12]
        base_dir = os.path.join(tempfile.gettempdir(), "md2edrawmind", job_id)
        os.makedirs(base_dir, exist_ok=True)
        md_path = os.path.join(base_dir, "input.md")
        with open(md_path, "wb") as fh:
            fh.write(data)

        with JOBS_LOCK:
            JOBS[job_id] = {"status": "running", "pct": 0, "message": "排队中",
                            "log": [], "files": [], "error": None}
        out_path = os.path.join(base_dir, "output.docx")
        threading.Thread(target=_run_job, daemon=True,
                         args=(job_id, md_path, out_path, os.path.join(base_dir, "work"), mix, limit)).start()
        return self._json({"job": job_id, "name": filename})


def _url_quote(name: str) -> str:
    from urllib.parse import quote
    return quote(name)


def run_server(host="127.0.0.1", port=8787, open_browser=True) -> int:
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = "http://%s:%d/" % (host, port)
    print("md2edrawmind GUI  →  %s" % url)
    print("（关闭这个窗口即停止服务）")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0
