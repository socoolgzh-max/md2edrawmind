# md2edrawmind v1.0.0

把带 LaTeX 公式的 Markdown 笔记，转成思维导图软件（EdrawMind 等）能直接导入的 Word 文件。

## 下载

**Windows 10 / 11。一个安装包，自带 Python 与 Node 运行时，不需要额外装任何东西。**

**md2edrawmind-1.0.0-setup.exe** · 42.7 MB

```
SHA256  32AEA19E932CBB1F97C4B693BC7A08F3B0389D8D70304DC52D99A659269F6ED7
```

下载后可用下面命令核对（应当输出上面这串）：

```powershell
Get-FileHash .\md2edrawmind-1.0.0-setup.exe -Algorithm SHA256
```

### 安装与使用

1. 双击安装，一路下一步（装在当前用户目录，**不需要管理员权限**）
2. 从开始菜单或桌面双击 `md2edrawmind`
3. 程序打开**自己的桌面窗口**（不会弹出黑色命令行窗口），窗口里就是操作界面
4. 把 `.md` 拖进去，转换完成后点「下载」，会弹出保存对话框让你选存放位置
5. 在思维导图软件里 **导入 → Word → 选刚保存的文件**

关闭窗口即退出程序，后台没有残留的控制台窗口；卸载走开始菜单里的「卸载 md2edrawmind」。

公式渲染会调用系统上已有的 Chrome 或 Edge 之一（Windows 一般自带 Edge）。

### 双击后没有任何反应？先解除锁定

这个版本没有代码签名证书。从浏览器下载的文件会被 Windows 打上「来自网络」标记，SmartScreen 可能**直接静默拦掉**，表现就是双击完全没反应（连报错都没有）。解决方式二选一：

- **推荐**：右键安装包 → 属性 → 常规页最下方勾选「解除锁定」→ 确定，然后再双击
- 或者在 PowerShell 里执行：

```powershell
Unblock-File .\md2edrawmind-1.0.0-setup.exe
.\md2edrawmind-1.0.0-setup.exe
```

如果弹出「Windows 已保护你的电脑」，点「更多信息」→「仍要运行」。

程序不联网、不上传任何内容；源码和打包脚本都在本仓库，可自行核对或自行构建。

## 出问题怎么查

程序启动与保存文件都会写日志：

```
%LOCALAPPDATA%\md2edrawmind\startup.log
```

把上面这行粘到文件管理器地址栏即可打开。日志会写明随包 Node 的位置、找到的浏览器、实际监听端口、保存到哪里，以及失败时的完整堆栈；启动失败时程序也会弹窗直接显示原因。

## 本版修复了什么

- **打包漏了 MathJax 的传递依赖 `mhchemparser`**：导致打包版渲染公式时 `Cannot find module`，界面表现为卡在 25% 报错。现已改为递归解析全部运行时依赖（9 个包）。
- **桌面窗口里点「下载」没反应**：pywebview 把 WebView2 的下载开关写死为 `ALLOW_DOWNLOADS=False`，且没有对外开关，链接下载会被静默取消。现改为调用原生「另存为」对话框，浏览器里仍走普通下载。
- **双击没反应无从排查**：旧启动器任何异常都静默退出。现在全流程写进 startup.log，失败弹原生对话框（GUI 子系统下没有控制台可看，日志是唯一线索）。

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
python tools/build_desktop.py --zip     # 绿色版目录 + zip
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
