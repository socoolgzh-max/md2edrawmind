# -*- coding: utf-8 -*-
"""验证打包好的桌面端：通过浏览器把真实 md 走完整流程，并校验产物。"""
import os
import zipfile

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8788"
MD = os.path.abspath("examples/考研数学-无穷级数.md")
DL = os.path.abspath("build/desktop-download")

os.makedirs(DL, exist_ok=True)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, headless=True,
                           args=["--disable-gpu", "--hide-scrollbars"])
    ctx = b.new_context(viewport={"width": 1000, "height": 760}, accept_downloads=True)
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(BASE)
    page.wait_for_timeout(600)

    env = page.inner_text("#envBadge")
    print("  界面环境状态:", env.strip())

    page.set_input_files("#file", MD)
    print("  已投递:", os.path.basename(MD), "(%.1f KB)" % (os.path.getsize(MD) / 1024))

    done = False
    for _ in range(90):
        page.wait_for_timeout(1000)
        st = page.evaluate("""() => ({
            msg: document.getElementById('msg').textContent,
            pct: document.getElementById('pct').textContent,
            stats: document.getElementById('stats').textContent,
            files: [...document.querySelectorAll('#files li b')].map(e => e.textContent),
        })""")
        if st["files"]:
            print("  完成: %s | %s | %s" % (st["msg"][:38], st["pct"], st["stats"]))
            for name in st["files"]:
                link = page.query_selector("#files a")
                with page.expect_download(timeout=20000) as dl_info:
                    link.click()
                d = dl_info.value
                target = os.path.join(DL, d.suggested_filename)
                d.save_as(target)
                print("    下载 %s  (%.1f KB)" % (d.suggested_filename, os.path.getsize(target) / 1024))
                page.wait_for_timeout(400)
                if page.query_selector("#files a"):
                    pass
            done = True
            break

    if not done:
        print("  未在 90s 内完成，最后状态:", page.inner_text("#msg"))
    print("  页面错误:", errs if errs else "无")
    b.close()

# 校验产物是合法 docx，且公式图片真的在里面
for f in os.listdir(DL):
    path = os.path.join(DL, f)
    if f.endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            media = [n for n in z.namelist() if n.startswith("word/media/")]
            doc = z.read("word/document.xml").decode("utf-8", "replace")
        print("  校验 %s: 公式图片 %d 张, outlineLvl 出现 %d 次"
              % (f, len(media), doc.count("outlineLvl")))
