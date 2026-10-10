# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2025-10-11

首个版本。目标只有一个：**让 AI 生成的带 LaTeX 公式的 Markdown，能带着公式进 EdrawMind**。

### Added

- **解析器 `md2edrawmind/parser.py`**：标题/列表层级、文字与公式拆分、三种公式位置策略
  （`tail` 公式挪到末尾 / `own` 公式单独成条 / `keep` 保持原句）。
- **公式渲染链路 `tools/render.js` + `tools/mathjax.js`**：
  MathJax v3 → SVG（字形转路径，无字体依赖）→ 精确坐标"公式表" → 无头浏览器一次性截图
  → 按坐标切成单张 PNG（自动去白边，分式/求和上下沿按 `viewBox` 纵横比保留）。
- **Word 生成 `md2edrawmind/docx_writer.py`**：写入 `w:outlineLvl` 建立层级、公式作为内嵌图片、
  按主题数上限自动切分（应对免费版 50 主题导入限制）。
- **本地 GUI `md2edrawmind/server.py` + `web/`**：纯标准库 `http.server`，
  拖拽上传、任务进度（SSE 实时推送）、结果下载；附 `?demo=1` 演示模式用于截图。
- **命令行 `md2edrawmind/cli.py`**：`convert` / `serve` / `check` / `install-tools`。
- **PyPI 打包**：`pyproject.toml` + `tools/sync_assets.py`，wheel 内含 web/tools 资源；
  `md2edrawmind install-tools` 为安装后的包补齐 Node 依赖。
- **测试**：`tests/test_parser.py`（解析/层级/公式位置/切分/大纲，含边界用例）、
  `tests/smoke_gui.py`（上传→进度→下载→校验 docx 的闭环）。
- **CI**：GitHub Actions，Windows + Python 3.10/3.12，跑单测与 MathJax 冒烟测试。
- **文档**：双语 README、`docs/FINDINGS.md`（逆向 EdrawMind 导入行为的完整记录）、
  演示 GIF（`tools/make_demo_gif.py` 自动生成，含真实产物预览）。
- **发布脚本**：`tools/publish_github.ps1`。

### Fixed

- 解析器 `_mixed()` 原地修改输入列表，导致一条主题被拆成多个节点。
- 按主题数切分时，**嵌套标题本身超出上限**会丢内容（现在递归下钻并保留祖先标题链）。
- 控制台为 GBK 时，输出 `⚠`/`✔` 会抛 `UnicodeEncodeError`（CLI 强制 UTF-8）。
- 公式图片被裁掉分式上下沿（高度改为按 SVG `viewBox` 纵横比计算）。

### Notes

- 已知限制见 README「Known limits」：公式在导图里是图片、不能二次编辑；
  PDF 导出仍受软件试用水印影响。
