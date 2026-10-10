# md2edrawmind

把 **AI 生成的带 LaTeX 公式的 Markdown 笔记**，一键转成**可以直接导入 EdrawMind（亿图脑图 / 万兴脑图）的 Word 文件**——
层级完整、公式保真显示、全程本地运行、不走云端 AI。

[English](README.md) · 中文

![演示](docs/demo.gif)

## 为什么需要它

用 AI 生成"无穷级数复习导图"这类带公式的笔记很爽，但**导入思维导图软件时公式会全军覆没**。
实测（EdrawMind 12.2.2）把坑挖清楚了：

| 导入方式 | 结果 |
| --- | --- |
| 导入 Markdown | ❌ 只认纯文本，`$...$` 原样变成文字 |
| 导入 HTML（走"智能解析"） | ❌ 走云端 AI：**简体被转成繁体**、层级丢失、公式变成标签 |
| 公式写成 Word 原生公式（OMML）再导入 Word | ❌ 它的 Word 导入器不解析 OMML，会把公式**拍平成字符**（`limn→∞Sn=S`） |
| 公式用 SVG 矢量图 | ❌ 导入器不认 SVG |
| **公式渲染成 PNG + 本地 Word 导入** | ✅ **保真显示**，且图片形式导出无水印 |

另外有个坑：**公式夹在文字中间会被它当成"批注"**（EdrawMind 的 bug），
所以本工具默认把公式**挪到主题末尾**（实测能正常显示的形态）。

## 安装

**从源码（推荐）：**

```bash
git clone https://github.com/SoCoolp/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt     # python-docx + Pillow
npm install                         # mathjax-full + pngjs（渲染公式）
python -m md2edrawmind check        # 环境自检
```

**从 PyPI 安装**（wheel 里不含 JS 渲染依赖，装一次即可）：

```bash
pip install md2edrawmind
md2edrawmind install-tools          # 自动为内置渲染器执行 npm install
md2edrawmind check
```

另外需要 **Chrome 或 Edge**（无头截图，会自动探测）和 **Node.js 18+**。

## 用法

### 图形界面（推荐）

```bash
python -m md2edrawmind serve
```

浏览器自动打开 `http://127.0.0.1:8787`：拖入 `.md` → 看进度 → 下载 `.docx` → EdrawMind「导入 → Word」。

### 命令行

```bash
python -m md2edrawmind convert 笔记.md                     # 输出 笔记.docx
python -m md2edrawmind convert 笔记.md -o 导图.docx --outline
python -m md2edrawmind convert 笔记.md --limit 46          # 按主题数上限自动切分
```

| 参数 | 说明 |
| --- | --- |
| `--mix tail` | **默认**。文字在前，公式统一挪到主题末尾（最稳） |
| `--mix own` | 公式单独成为一条子主题 |
| `--mix keep` | 保持原句顺序（公式夹在中间会变批注） |
| `--limit N` | 每个文件最多 N 个主题，超出自动切分（EdrawMind 免费版导入上限 50） |
| `--outline` | 同时导出纯文本大纲（制表符缩进，备用导入方式） |

## 工作流程

```
笔记.md
  ├─ parser.py        解析层级 / 拆分文字与公式 / 公式位置策略
  ├─ render.js        MathJax → SVG（字形转路径，无字体依赖）
  │                   → 排成精确坐标的"公式表"
  ├─ Chrome 无头截图   一次性把所有公式渲染成高清图
  ├─ render.js slice  按坐标切成一张张 PNG（去白边）
  └─ docx_writer.py   写 w:outlineLvl 层级 + 内嵌公式图片
```

## 已知限制

- 主体是**为 EdrawMind 的导入行为定制**的；换其他思维导图软件（XMind、MindManager）需要另测导入格式。
- 公式在导图里是**图片**，不能像公式对象那样再编辑（EdrawMind 的 Word 导入不支持 OMML，这是它的限制）。
- 图片形式的公式**导出 PNG/JPG 不加水印**，但**导出 PDF 仍会带试用水印**（软件策略）。
- 浏览器截图这一步依赖窗口高度；超长公式表可以调大 `tools/render.js` 里的 `--window-size`。

## 开发

```bash
python -m md2edrawmind check          # 环境自检
python tests/test_parser.py           # 解析器 / docx 单元测试
python tests/smoke_gui.py 8899        # GUI 闭环冒烟测试（上传→进度→下载→校验 docx）
python tools/make_demo_gif.py         # 重新生成 docs/demo.gif
node tools/render.js tex2svg work     # 只出矢量 SVG（不需要浏览器）
```

## License

MIT
