# -*- coding: utf-8 -*-
"""冒烟测试：起服务、上传示例 md、跟随进度、下载结果并校验 docx。

用法: python tests/smoke_gui.py [port]
"""
import io
import json
import os
import re
import sys
import threading
import time
import urllib.request
import uuid
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from _utf8 import ensure_utf8                        # noqa: E402
from md2edrawmind.server import run_server           # noqa: E402

ensure_utf8()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
BASE = "http://127.0.0.1:%d" % PORT
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def post_multipart(url, fields, filename, filedata):
    boundary = uuid.uuid4().hex
    buf = io.BytesIO()
    for k, v in fields.items():
        buf.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode())
    buf.write(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
               "Content-Type: text/markdown\r\n\r\n" % (boundary, filename)).encode())
    buf.write(filedata)
    buf.write(("\r\n--%s--\r\n" % boundary).encode())
    req = urllib.request.Request(url, data=buf.getvalue(),
                                 headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    t = threading.Thread(target=run_server, kwargs={"port": PORT, "open_browser": False}, daemon=True)
    t.start()
    time.sleep(1.5)

    md_path = os.path.join(ROOT, "tests", "fixture.md")
    md = open(md_path, "rb").read() if os.path.exists(md_path) else b"# t\n\n- $a^2+b^2=c^2$\n"

    print("[1] 上传", len(md), "bytes")
    res = post_multipart(BASE + "/api/upload", {"mix": "tail", "limit": "0"}, "fixture.md", md)
    job = res["job"]
    print("    job =", job)

    print("[2] 跟随进度")
    last = None
    deadline = time.time() + 180
    final = None
    while time.time() < deadline:
        req = urllib.request.Request(BASE + "/api/progress/" + job)
        with urllib.request.urlopen(req, timeout=30) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data = json.loads(line[5:].strip())
                if data.get("message") != last:
                    last = data.get("message")
                    print("    %3d%%  %s" % (data.get("pct", 0), last))
                if data.get("status") in ("done", "error"):
                    final = data
                    break
        if final:
            break
        time.sleep(0.5)

    if not final:
        print("✗ 超时"); return 1
    if final.get("status") == "error":
        print("✗ 转换失败:", final.get("error")); return 1

    print("[3] 下载并校验")
    files = final.get("files") or []
    ok = True
    for i, f in enumerate(files):
        with urllib.request.urlopen("%s/api/download/%s/%d" % (BASE, job, i), timeout=60) as r:
            blob = r.read()
        path = os.path.join(ROOT, "build", "smoke_%d.docx" % i)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(blob)
        z = zipfile.ZipFile(io.BytesIO(blob))
        doc = z.read("word/document.xml").decode("utf-8")
        levels = re.findall(r'w:outlineLvl w:val="(\d+)"', doc)
        imgs = doc.count("<w:drawing>")
        print("    %s  %d bytes  层级=%s  公式图=%d" %
              (f["name"], len(blob), sorted(set(levels)), imgs))
        ok = ok and bool(levels) and imgs > 0

    print("\n结论:", "GUI 闭环通过 ✔" if ok else "有问题 ✘")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
