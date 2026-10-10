# -*- coding: utf-8 -*-
"""生成 README 用的演示 GIF（拖入 → 转换进度 → 完成 → 导入后的导图）。

需要在项目根目录运行，并且 PATH 里有 python/node，Chrome 在默认位置。

用法: python tools/make_demo_gif.py [端口]
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageSequence          # noqa: E402

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
FRAMES = os.path.join(ROOT, "build", "gif")
OUT = os.path.join(ROOT, "docs", "demo.gif")


def chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    exe = shutil.which("chrome") or shutil.which("msedge")
    if not exe:
        raise SystemExit("找不到 Chrome/Edge")
    return exe


def shot(url, path, size=(1000, 800)):
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--no-first-run", "--force-device-scale-factor=1",
                    "--window-size=%d,%d" % size, "--virtual-time-budget=2500",
                    "--screenshot=" + path, url], capture_output=True, timeout=120)
    if not os.path.exists(path):
        raise SystemExit("截图失败: " + path)


def find_node(min_major=18):
    """找一个足够新的 node（LibreOffice Kit CLI 需要 22+）"""
    cands = [r"D:\Tool\DSharness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe",
             r"C:\Program Files\nodejs\node.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs\node.exe"),
             shutil.which("node"),
             r"D:\Envirment\nvm\nodejs\node.exe"]
    fallback = None
    for c in cands:
        if not c or not os.path.exists(c):
            continue
        try:
            out = subprocess.run([c, "-v"], capture_output=True, timeout=20).stdout.decode().strip()
            major = int(out.lstrip("v").split(".")[0])
        except Exception:
            continue
        if major >= min_major:
            return c
        fallback = fallback or c
    return fallback


def find_lo_cli():
    for cand in (
        r"D:\Tool\DSharness\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js",
        os.path.join(os.path.dirname(sys.executable), "..", "libreoffice-kit", "lib", "cli.js"),
    ):
        if os.path.exists(cand):
            return cand
    env = os.environ.get("MD2EDRAW_LO_CLI")
    return env if env and os.path.exists(env) else None


def render_docx_png(docx, out_png, size=(1000, 800)):
    """用 LibreOffice Kit 把 docx 首页渲染成 PNG（可选：没有就少一帧）"""
    node = find_node()
    cli = find_lo_cli()
    if not node or not cli or not os.path.exists(docx):
        return None
    tmp = os.path.join(FRAMES, "docx-preview")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        p = subprocess.run([node, cli, "render", "--input", docx, "--output-dir", tmp,
                            "--pages", "1", "--dpi", "80"], capture_output=True, timeout=180)
        if p.returncode != 0:
            print("    [warn] docx 预览渲染失败:", (p.stderr or b"").decode("utf-8", "replace")[:160])
    except Exception as err:
        print("    [warn] docx 预览渲染异常:", err)
        return None
    src = os.path.join(tmp, "page-0001.png")
    if not os.path.exists(src):
        return None
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", size, (255, 255, 255))
    im.thumbnail((size[0] - 60, size[1] - 60))
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    canvas.save(out_png)
    return out_png


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8795
    os.makedirs(FRAMES, exist_ok=True)
    base = "http://127.0.0.1:%d" % port

    print("[1] 启动 GUI …")
    proc = subprocess.Popen([sys.executable, "-m", "md2edrawmind", "serve",
                             "--port", str(port), "--no-browser"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            urllib.request.urlopen(base + "/api/env", timeout=2).read()
            break
        except Exception:
            time.sleep(0.4)
    else:
        proc.terminate()
        raise SystemExit("GUI 启动失败")

    try:
        print("[2] 截帧：空界面 / 进度 / 完成")
        shot(base + "/?demo=1", os.path.join(FRAMES, "f1.png"))
        shot(base + "/?demo=1&state=progress", os.path.join(FRAMES, "f2.png"))
        shot(base + "/?demo=1&state=done", os.path.join(FRAMES, "f3.png"))
    finally:
        proc.terminate()

    frames = [os.path.join(FRAMES, "f1.png"), os.path.join(FRAMES, "f2.png"), os.path.join(FRAMES, "f3.png")]

    print("[3] 用真实产物生成一帧 docx 预览")
    docx = os.path.join(ROOT, "build", "demo.docx")
    if not os.path.exists(docx):
        subprocess.run([sys.executable, "-m", "md2edrawmind", "convert",
                        os.path.join(ROOT, "examples", "考研数学-无穷级数.md"),
                        "-o", docx], cwd=ROOT, capture_output=True)
    prev = render_docx_png(docx, os.path.join(FRAMES, "f4.png"))
    if prev:
        frames.append(prev)

    print("[4] 合成 GIF")
    imgs = []
    for f in frames:
        im = Image.open(f).convert("RGB")
        imgs.append(im)
    # 统一尺寸
    w = min(i.width for i in imgs)
    h = min(i.height for i in imgs)
    imgs = [i.crop((0, 0, w, h)) for i in imgs]
    # 每帧时长：界面帧快一点，结果帧停久一点
    durations = [900, 700, 2200] + ([2600] if len(imgs) > 3 else [])
    durations = durations[:len(imgs)]
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=durations,
                 loop=0, optimize=True)
    print("完成 →", OUT, os.path.getsize(OUT) // 1024, "KB", "帧数", len(imgs))


if __name__ == "__main__":
    main()
