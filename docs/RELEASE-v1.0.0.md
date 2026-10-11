# md2edrawmind v1.0.0

把带 LaTeX 公式的 Markdown 笔记，转成思维导图软件（EdrawMind 等）能直接导入的 Word 文件。

## 下载

| 文件 | 适用 | 说明 |
|---|---|---|
| **md2edrawmind-1.0.0-setup.exe** | Windows 10 / 11 | 安装版（推荐）。创建开始菜单与桌面快捷方式，可从开始菜单卸载 |
| **md2edrawmind-windows-x64.zip** | Windows 10 / 11 | 免安装绿色版。解压后双击 `md2edrawmind.exe` |

两种方式都**自带 Python 与 Node 运行时**，不需要你装任何东西。公式渲染会调用系统上已有的 Chrome 或 Edge（Windows 一般自带 Edge）。

### 安装版怎么用

1. 双击 `md2edrawmind-1.0.0-setup.exe`，一路下一步（装在当前用户目录，不需要管理员权限）
2. 从开始菜单或桌面双击 `md2edrawmind`
3. 程序会自动在浏览器里打开操作界面，地址形如 `http://127.0.0.1:8787/`
4. 把 `.md` 拖进去，下载生成的 `.docx`
5. 在思维导图软件里 **导入 → Word → 选该文件**

关掉那个黑色命令行窗口即停止服务。

### 如果 Windows 弹出安全提醒

这个版本没有代码签名证书，从浏览器下载后 Windows SmartScreen 可能提示「未知发布者」。

- 安装版：点「更多信息」→「仍要运行」即可
- 绿色版：先右键 zip → 属性 → 勾选「解除锁定」，再解压（否则解压出来的 exe 会被系统拦住）

程序不联网、不上传任何内容；源码与构建脚本都在本仓库，可自行核对或自行打包。

## 出问题怎么查

程序启动的每一步都会写进日志：

```
%LOCALAPPDATA%\md2edrawmind\startup.log
```

把上面这行粘到文件管理器地址栏即可打开。日志会写明随包 Node 的位置、找到的浏览器、实际监听端口，以及启动失败时的完整堆栈；启动失败时程序也会弹窗直接显示原因。

## 为什么公式不会丢

思维导图软件读 Markdown 时把 `$...$` 当纯文本，所以公式会变成 `\lim_{n \to \infty} S_n = S` 这种乱码，或者被压成 `limn→∞Sn=S`。这个工具换了一条路：

- 用 MathJax 把每条公式渲染成图片，嵌进 Word
- 用 `w:outlineLvl` 保住标题层级（缩进和加粗无效，必须这个标记）
- 公式放在主题文字**末尾**：夹在文字中间会被软件识别成批注

全程离线，不上传任何内容。

## 从源码运行

```bash
git clone https://github.com/socoolgzh-max/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt && npm install
python -m md2edrawmind check        # 检查 Python / Node / 浏览器
python -m md2edrawmind serve        # 打开界面
```

自己打包：

```bash
python tools/build_desktop.py --zip     # 绿色版 + zip
python tools/build_installer.py         # 安装版（需要 Inno Setup 6）
```

## 已知限制

- 目前只有 Windows x64 构建
- 公式在导图里是**图片**，不能再编辑（EdrawMind 的 Word 导入不解析 OMML）
- PDF 导出会带软件试用版水印，PNG / JPG 导出没有
- 若系统未安装 Chrome / Edge，公式无法转成图片

## 校验

用真实笔记验证过：94 个主题、113 条公式，生成的 docx 含 85 张公式图（重复公式复用同一张）与 94 个 `outlineLvl`。

```bash
python tests/test_parser.py     # 解析与 Word 生成单测
python tests/smoke_gui.py 8931  # 界面闭环冒烟
```
