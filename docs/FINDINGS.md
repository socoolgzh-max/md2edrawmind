# 逆向发现：EdrawMind 的导入行为

这份文档记录本项目**实测得出**的结论（EdrawMind 12.2.2 / 万兴脑图，Windows）。
写下来是为了让后来者不用重走一遍——每一条都对应一次失败尝试。

环境：`E:\App\MindMaster`，`EdrawMind.exe` 文件版本 **12.2.2.1053**。

---

## 1. 各种导入方式的真实结果

| 导入方式 | 内部实现（从可执行文件里读到的） | 公式 | 文字 | 层级 |
| --- | --- | --- | --- | --- |
| Markdown | `MainWindow::importMarkdownFile`（本地） | ❌ 原样文字 | ✅ | ✅ |
| HTML / 网页 | **云端 AI 解析**：`/ai/pptParse/parseFile`，带 `parse_type=` 参数 | ❌ 变标签 | ⚠️ **简体被转成繁体** | ❌ 塌成平铺 |
| Word `.docx` | `WordImporter::importWordFile`（本地） | ⚠️ 见下 | ✅ | 需 `w:outlineLvl` |
| XMind / FreeMind / MindManager | 各自独立的本地 Importer | 未测 | — | — |
| 纯文本 `.txt` | 本地 | ❌ | ✅ | ✅ |

结论：**要公式，就必须走本地导入（Word）**；HTML 那条路是云端 AI，既不可控又会改字。

## 2. Word 导入的细节（本项目踩过的坑）

### 2.1 OMML（Word 原生公式）不被支持
把公式写成 OMML（`<m:oMath>`）再导入，**公式会被拍平成字符**：

```
\lim_{n \to \infty} S_n = S   →   limn→∞Sn=S
\rho = \lim \frac{u_{n+1}}{u_n}  →  ρ=limn→∞un+1un
```

它的导入器只是把 `m:t` 里的文本抽出来拼在一起。**所以公式只能用图片承载。**

### 2.2 层级必须写 `w:outlineLvl`
只靠"标题样式 + 字体加粗 + 左缩进"，导入后**所有主题会平铺在中心主题下**。
写入 `<w:outlineLvl w:val="N"/>` 后层级才正常（N=0 为第一层）。

### 2.3 图片公式**不能夹在文字中间**
一条主题里，如果元素顺序是 `文字 → 图片 → 文字`，**公式会掉进"批注/注释"里**（界面上表现为一个便签角标）。
实测可行的是：

- `文字 → 图片`（公式在**末尾**）✅
- `图片` 单独成条 ✅
- `图片 → 文字` ⚠️ 视情况

所以本项目默认 `--mix tail`：**把公式统一挪到主题末尾**。

### 2.4 SVG 不被接受
公式用矢量 SVG 引入会失败；必须栅格化成 PNG。本项目用 Chrome 无头截图把 MathJax 的 SVG 批量转成 PNG。

## 3. `.emmx` 文件内部（了解边界用）

`.emmx` 就是一个 ZIP：

```
document.xml          文档属性、标记表、页面索引
mm.bkiwi              最近使用等杂项
mmpage/page.bin       ★ 正文（自定义二进制序列化）
media/img*.png        ★ 公式的渲染图
rels/page_formats.xml theme.xml
```

`page.bin` 里文本是 **UTF-8 明文**，但整体是**带索引的自定义序列化**（小整数 token + 长度前缀）。
公式对象在其中长这样：

```
...并行访问方式： <bin> 1 png 2 3 <math display="block"
   xmlns="http://www.w3.org/1998/Math/MathML" mathcolor="rgb(0, 0, 0)">
   <mrow><msub>...</msub>...</mrow></math> ...
```

即：**MathML 文本 + 一张同名 PNG + 图片序号**。

> 我们**没有**直接生成 `page.bin`：它是索引化二进制，逆错会产出打不开的文件，
> 性价比远低于"渲染成图片 + 走 Word 导入"。这里记录下来，供将来想做原生公式对象的人接手。

## 4. 免费版 / 会员限制（字符串原文）

```
Currently, you are using the free version, which is limited to 50 topics when importing Word/HTML/Markdown.
Free version supports importing Word/HTML/Markdown with only up to 50 nodes
Currently, you are using the free version, which is limited to 100 topics.
Inserting formulas is exclusive to members
```

- 「插入公式」（Ctrl+Shift+L）是**会员功能**；
- 免费版**导入上限 50 个主题** → 本项目提供 `--limit N` 自动切分；
- 图片形式的公式在 **PNG/JPG 导出无水印**，但 **PDF 导出仍带试用水印**。

## 5. 公式键盘与对话框（供自动化参考）

公式编辑器是独立的 CEF 窗口（标题 `公式編輯器 EdrawMath`），源文件在
`Config/formula/index.html` + `Config/formula/EDMath/*.js`（内含 `edlatextomml.js` / `edmmltolatex.js`）。

它的前端源码逻辑：

```js
// Ctrl+Enter 只是"转换预览"
(l.ctrlKey && (l.key.toLowerCase() === "enter" || l.keyCode === 13)) &&
  (t.value === Eu.math ? Bt.emit("confirmMath") : Bt.emit("confirmLatex"))

// 真正保存：Vue 的保存按钮 → applyFormula → hidePcDialogLatex
Bt.on("hidePcDialogLatex", () => { ...; window.$qt.jsCallHideDialog(s.value, imgUrl, "png") })
```

值得注意的是：**这个窗口对 Windows UI Automation 不可见**（枚举不到控件），
PrintWindow 截图也是空白（CEF 离屏渲染）——所以"逐条自动插公式"这条路没有可靠的验证手段，
本项目因此选择了"渲染成图片"的方案。

## 6. 结论：为什么是现在这套方案

```
Markdown → 解析 → 公式用 MathJax 渲染成 PNG → 生成带 w:outlineLvl 的 .docx → 本地 Word 导入
```

它同时满足：公式可见、层级正确、文字不被改写、全程离线、导出 PNG/JPG 无水印。
