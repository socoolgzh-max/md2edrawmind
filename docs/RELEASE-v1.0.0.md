# md2edrawmind v1.0.0

把带 LaTeX 公式的 Markdown 笔记，转成思维导图软件（EdrawMind 等）能直接导入的 Word 文件。

## 下载

| 文件 | 说明 |
|---|---|
| **md2edrawmind-windows-x64.zip** | Windows 10 / 11 桌面端，解压后双击 `md2edrawmind.exe` 即用 |

桌面端**自带 Python 与 Node 运行时**，不需要安装任何东西。公式渲染会调用你系统上已装的 Chrome 或 Edge（Windows 一般都自带 Edge）。

## 它是怎么用的

1. 解压 zip，双击 `md2edrawmind.exe`
2. 浏览器自动打开本地界面（地址形如 `http://127.0.0.1:8787/`）
3. 把你的 `.md` 拖进去
4. 下载生成的 `.docx`，在思维导图软件里 **导入 → Word → 选该文件**

关掉那个黑色窗口即停止服务。

## 为什么公式不会丢

思维导图软件读 Markdown 时把 `$...$` 当纯文本，所以公式会变成 `\lim_{n \to \infty} S_n = S` 这种乱码，或者被压成 `limn→∞Sn=S`。这个工具换了一条路：

- 用 MathJax 把每条公式渲染成图片，嵌进 Word
- 用 `w:outlineLvl` 保住标题层级（缩进和加粗是无效的，必须这个标记）
- 公式放在主题文字**末尾**：夹在文字中间会被软件识别成批注

全程离线，不上传任何内容。

## 从源码运行

```bash
git clone https://github.com/socoolgzh-max/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt && npm install
python -m md2edrawmind check        # 检查 Python / Node / 浏览器
python -m md2edrawmind serve        # 打开界面
```

自己打包桌面端：

```bash
python tools/build_desktop.py --zip
```

## 已知限制

- 桌面端目前只提供 Windows x64 构建
- 公式在图里是**图片**，导图里不能再编辑（EdrawMind 的 Word 导入不解析 OMML）
- PDF 导出会带软件试用版水印，PNG / JPG 导出没有
- 若系统未安装 Chrome / Edge，公式无法转成图片

## 校验

产物用真实笔记验证过：94 个主题、113 条公式，生成的 docx 含 85 张公式图（重复公式复用同一张）与 94 个 `outlineLvl`。

```bash
python tests/test_parser.py     # 解析与 Word 生成单测
python tests/smoke_gui.py 8931  # 界面闭环冒烟
```
